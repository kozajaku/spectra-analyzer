import os
import io
import base64
from astropy.io import fits, votable
import numpy
import mlpy.wavelet as wave
import matplotlib.pyplot as plt
import warnings


class SpectrumFileReader:
    """Abstract class for individual readers. Every reader can read its own type
    of spectrum format."""

    def _scidata(self, fits_file):
        """
        This method must be overrided in subclasses. It returns pure y spectrum values
        in the same way as they were written in the source spectrum file.
        :param fits_file: Path to an existing file containing spectrum data.
        :return: 1D numpy array of y values.
        """
        pass

    def normalized(self, fits_file):
        """
        Function takes spectrum file as an argument and returns y spectrum values
        normalized to range [0, 1]
        :param fits_file:
        :return:
        """
        data = self._scidata(fits_file)
        # normalization
        data = (data - min(data)) / (max(data) - min(data))
        return data


class FitReader(SpectrumFileReader):
    """Specific spectrum reader. Uses astropy.io.fits API for fetching FITS spectrum file
    in the image/fits (older) standard. This standard does NOT contain x spectrum values."""

    def _scidata(self, file_path):
        hdulist = fits.open(file_path)
        scidata = hdulist[0].data
        hdulist.close()
        return scidata


class FitsReader(SpectrumFileReader):
    """Specific spectrum reader. Uses astropy.io.fits API for fetching FITS spectrum file
    in the application/fits (newer) standard. This format should contain more metadata
    and moreover it should also contain x spectrum values."""

    def _scidata(self, fits_file):
        hdulist = fits.open(fits_file)
        scidata = hdulist[1].data
        detupled = numpy.zeros(shape=scidata.shape)
        for i in range(scidata.shape[0]):
            detupled[i] = scidata[i][1]
        scidata = detupled
        hdulist.close()
        return scidata


class SimpleTextReader(SpectrumFileReader):
    """Specific spectrum reader. File in simple text format
    contains x and y on rows separated by a specific separator."""

    def __init__(self, separator):
        self.separator = separator

    def _scidata(self, file_path):
        s = numpy.genfromtxt(file_path, delimiter=self.separator)
        s = s[:, 1]
        return s


class VotReader(SpectrumFileReader):
    """Specific spectrum reader. Uses astropy.io.votable API for fetching vot spectrum file
    supported are both binary and text column based votables."""

    def _scidata(self, file_path):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            vot = votable.parse(file_path)
        table = vot.get_first_table()
        data = table.array
        detupled = numpy.zeros(shape=data.shape)
        for i in range(data.shape[0]):
            detupled[i] = data[i][1]
        return detupled


EXTENSION_MAPPING = {
    "fit": FitReader(),
    "fits": FitsReader(),
    "vot": VotReader(),
    "asc": SimpleTextReader("  "),
    "csv": SimpleTextReader(","),
    "txt": SimpleTextReader("\t"),
}


class Spectrum:
    @classmethod
    def read_spectrum(cls, file_path):
        """
        Factory method for Spectrum class. It creates new instance of the class
        by passing path to the spectrum file. If the reader was unable to properly
        parse a passed spectrum this function returns None.
        :param file_path: Filesystem path to the spectrum file
        :return: Spectrum instance if spectrum reading was successful. None otherwise.
        """
        if not os.path.isfile(file_path):
            raise ValueError("Spectrum file does not exist")
        # find out file extension
        extension = file_path.split(".")[-1]
        reader = EXTENSION_MAPPING.get(extension)
        if reader is None:
            return None
        try:
            return cls(reader.normalized(file_path))
        except Exception as ex:
            import traceback
            print(traceback.format_exc())
            return None

    def __init__(self, spectrum):
        """Initializes instance of Spectrum class."""
        self.spectrum = spectrum
        self.scales = wave.autoscales(N=spectrum.shape[0], dt=1, dj=0.25, wf='dog', p=2)
        self.freq0 = 0
        self.wSize = 5 if len(self.scales) > 5 else len(self.scales) - 1
        self._transformation = wave.cwt(spectrum, dt=1, scales=self.scales, wf='dog', p=2)
        self._rec = None

    @staticmethod
    def _plot_to_base64():
        """Convert currently plotted figure into png image encoded as base64 string. Also closes figure
        after plotting to release memory."""
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        img = base64.b64encode(buf.getvalue()).decode("ascii")
        buf.close()
        plt.close()
        return img

    def _recount_rec(self):
        """This method recounts reduced spectrum and saves it as an instance attribute."""
        # do "dog" wavelet transformation
        concatenated = numpy.concatenate((
            self._transformation[:self.freq0], numpy.zeros((self.wSize, len(self.spectrum))),
            self._transformation[self.freq0 + self.wSize:]))
        self._rec = wave.icwt(concatenated, dt=1, scales=self.scales, wf='dog', p=2)
        # normalize
        self._rec = (self._rec - min(self._rec)) / (max(self._rec) - min(self._rec))

    def modify_parameters(self, freq0, wSize):
        """
        This method modifies transformation parameters saved in the class. It also
        provides boundary checks. If parameters are out of boundary, wSize parameter is adjusted to
        match correct settings.
        :param freq0: Frequency shift parameter. This parameter bust be in range [0, len(scales) - wSize].
        :param wSize: Window size parameter. This parameter must be in range [0, len(scales) - 1 - freq0].
        """
        sl = len(self.scales)
        if freq0 < 0:
            freq0 = 0
        elif freq0 > sl:
            freq0 = sl
        if wSize < 0:
            wSize = 0
        elif wSize > sl - 1 - freq0:
            wSize = sl - 1 - freq0
        self.freq0 = freq0
        self.wSize = wSize
        # invalidate _rec
        self._rec = None

    def plot_spectrum(self):
        """
        Returns plotted spectrum as a png image encoded in base64 format.
        :return: PNG image encoded as Base64 string.
        """
        plt.figure(figsize=(15, 2))
        plt.plot(self.spectrum)
        return self._plot_to_base64()

    def plot_cwt(self):
        """
        Returns image representation of continuous wavelet transformation.
        :return: PNG image encoded as Base64 string.
        """
        plt.figure(figsize=(15, 2))
        plt.imshow(numpy.abs(self._transformation), aspect="auto")
        return self._plot_to_base64()

    def plot_reduced_spectrum(self, only_transformation=False):
        """
        Do a wavelet transformation - dimension reduction method. Returns a png image of
        the spectrum before and after transformation encoded in base64 format.
        :param only_transformation: Specifies, that only transformation graph should be plotted.
        If set as False (implicit) both graph (old and new spectrum) are plotted.
        :return: PNG image encoded as Base64 string.
        """
        if self._rec is None:
            self._recount_rec()
        plt.figure(figsize=(15, 5))
        plt.plot(self._rec)
        if not only_transformation:
            plt.plot(self.spectrum, alpha=0.8)
        return self._plot_to_base64()
