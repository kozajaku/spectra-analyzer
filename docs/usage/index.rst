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

.. toctree::
    :maxdepth: 2
