Installation
============

When you have properly downloaded source codes, you can now proceed with installation of dependencies and then
installation of tool itself. Before installation, I really recommend to setup new Python
virtual environment if you have not done this yet. You can find information about how to do in :doc:`virtualenv`.

Install Spectrum downloader
---------------------------

First you have to install spectrum downloader. To install it you will have to clone the
`GitHub <https://github.com/kozajaku/spectra-downloader>`_ repository and invoke::

    python3 setup.py install

in the newly clonned directory. For more information about Spectra downloader installation see its documentation
`GitHub <https://github.com/kozajaku/spectra-analyzer>`_.

Install mlpy
------------

Spectra analyzer tool requires **mlpy** for the continual wavelet transformation function. This Python
library is not published on PyPi (the one published there is the different package!). To install **mlpy**
just follow the installation guide on `SourceForge <http://mlpy.sourceforge.net/docs/3.5/install.html>`_. Do not
forget to install the **GSL** library together with header files or your compilation will fail. You can install
this library on Linux systems using package managers (gsl-dev/gsl-devel).

Note that **mlpy** requires a specific version of **numpy** library. The specific version will be installed
automatically when you follow next steps. The newer version of **numpy** library is currently not working with
the latest version of **mlpy** library.

Install Spectra analyzer
------------------------

Now when you have all unpublished dependencies installed you can use already created ``setup.py`` file to make the rest
of installation really simple.

First navigate to the root directory of the **spectra_analyzer** tool. ``setup.py`` file should be in this directory too.
Now you can invoke installation process by calling::

    python3 setup.py install
