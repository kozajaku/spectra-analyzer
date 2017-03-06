from setuptools import setup, find_packages

with open('README.rst') as f:
    long_description = ''.join(f.readlines())

setup(
    name='spectra_analyzer',
    version='0.1',
    description='WebSocket based web application for downloading and analyzing astronomical spectra.',
    long_description=long_description,
    author='Jakub Koza',
    author_email='kozajaku@fit.cvut.cz',
    keywords='astronomy,spectra,spectrum,cwt',
    license='MIT',
    url='https://github.com/kozajaku/spectra-analyzer',
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3 :: Only',
    ],
    entry_points={
        'console_scripts': [
            'spectra_analyzer = spectra_analyzer.server:main',
        ],
    },
    install_requires=['spectra_downloader', 'click', 'flask', 'eventlet', 'flask-socketio',
                      'astropy', 'numpy==1.11.2', 'matplotlib', 'scipy'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
)
