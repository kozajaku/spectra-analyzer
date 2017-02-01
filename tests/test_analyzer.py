import pytest
import os
from tests import test_analyzer
from spectra_analyzer import analyzer


def file_ref(name):
    """Helper function for getting paths to testing spectra."""
    file = os.path.join(os.path.dirname(test_analyzer.__file__),
                        "test_analyzer", name)
    return file


def normalized(spectrum):
    """Test if passed spectrum is truly normalized."""
    for i in range(spectrum.shape[0]):
        if spectrum[i] < 0.0 or spectrum[i] > 1.0:
            return False
    return True


@pytest.fixture
def spectrum_inst():
    """Returns instance of Spectrum class for further testing."""
    spectrum_file = file_ref("binary.vot")
    return analyzer.Spectrum.read_spectrum(spectrum_file)


@pytest.mark.parametrize("file", ["binary.vot", "spectrum.asc", "spectrum.csv", "spectrum.fits",
                                  "spectrum.fit", "spectrum.txt", "tabledata.vot"])
def test_fit_reader(file):
    """Test spectrum reader for individual spectra formats."""
    spectrum_file = file_ref(file)
    res = analyzer.Spectrum.read_spectrum(spectrum_file)
    assert res is not None
    assert normalized(res.spectrum)


def test_trans_parameters(spectrum_inst):
    """Test modification of transformation parameters inside spectrum instance."""
    # test initial parameters
    assert spectrum_inst.freq0 == 0
    assert spectrum_inst.wSize == 5
    scales = len(spectrum_inst.scales)
    assert scales == 48  # set for the specific spectrum
    mod = spectrum_inst.modify_parameters
    mod(48, 0)
    assert spectrum_inst.freq0 == 47
    assert spectrum_inst.wSize == 0
    mod(48, 10)
    assert spectrum_inst.freq0 == 47
    assert spectrum_inst.wSize == 0
    mod(48, 1)
    assert spectrum_inst.freq0 == 47
    assert spectrum_inst.wSize == 0
    mod(47, 1)
    assert spectrum_inst.freq0 == 47
    assert spectrum_inst.wSize == 0
    mod(46, 2)
    assert spectrum_inst.freq0 == 46
    assert spectrum_inst.wSize == 1
    mod(0, 48)
    assert spectrum_inst.freq0 == 0
    assert spectrum_inst.wSize == 47
    mod(0, 47)
    assert spectrum_inst.freq0 == 0
    assert spectrum_inst.wSize == 47
    mod(1, 47)
    assert spectrum_inst.freq0 == 1
    assert spectrum_inst.wSize == 46


def test_spectrum_plotting(spectrum_inst):
    """Test that spectrum plotting returns some output."""
    plot = spectrum_inst.plot_spectrum()
    assert type(plot) == str
    assert len(plot) > 0


def test_cwt_plotting(spectrum_inst):
    """Test that cwt plotting returns some output."""
    plot = spectrum_inst.plot_cwt()
    assert type(plot) == str
    assert len(plot) > 0


def test_transformation_plotting(spectrum_inst):
    """Test that transformation plotting returns some output."""
    plot = spectrum_inst.plot_reduced_spectrum()
    assert type(plot) == str
    assert len(plot) > 0
    plot = spectrum_inst.plot_reduced_spectrum(only_transformation=True)
    assert type(plot) == str
    assert len(plot) > 0


def test_rec_invalidation(spectrum_inst):
    """Test that _rec variable is properly invalidated after parameter modification."""
    assert spectrum_inst._rec is None
    spectrum_inst.plot_reduced_spectrum()
    assert spectrum_inst._rec is not None
    spectrum_inst.modify_parameters(5, 4)
    assert spectrum_inst._rec is None
