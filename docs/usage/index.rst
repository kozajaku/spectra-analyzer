Usage
=====

To start the Spectra analyzer tool simply execute in the console::

    spectra_analyzer

or::

    python -m spectra_analyzer

The tool will start HTTP server listening implicitly on localhost with port 5000. You simple
have to open your favourite web browser and add http://127.0.0.1:5000 as your URL address. You can
also change hostname and port parameters::

    spectra_analyzer --host 0.0.0.0 --port 6789

For more information execute::

    spectra_analyzer --help

Example use case
----------------

Let's simulate work with the Spectra analyzer tool. At first you need to download some spectra. Let's say you have
the following link for SSAP query::

    http://voarchive.asu.cas.cz/ccd700/q/ssa/ssap.xml?REQUEST=queryData&MAXREC=40&TARGETNAME=HD217476

Work with Downloader is really simple:

- Select Download VOTABLE from URL
- Insert URL address
- Click Process
- Select which spectra in the selection list you want to download
- Add parameters for DataLink protocol or leave empty (or disable DataLink to use direct access)
- Insert target directory on filesystem where the spectra should be downloaded to
- Click Start downloading

Now you can see the spectra download progress. You can now move to Analyzer page for some spectra
analyzing.

- Navigate to spectra directory (you can either directly input path or navigate through directories by clicking on table items
- Click on selected spectrum in a table
- Wait for analyze to finish

Now you are able to see a plotted spectrum and its transformation. You can adjust parameters
by moving sliders and you can also hide the plot of original spectrum. Feel free to select
another spectrum file in a table to continue analysis with different spectrum.


.. toctree::
    :maxdepth: 2
