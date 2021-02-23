##### Building locally

First create a virtual environment with your favorite tool, and activate eg
```bash
python3.8 -m venv venv
source venv/bin/activate
```

Install and test with make
```bash
make
```

Or with flit
```
pip install flit
flit install --deps develop --symlink
```

##### Linting and Formatting
TODO - write some docs on linting on formating

Lint with flake8, black, and isort
```bash
make lint
```

Format with autoflake, black, and isort (updates files in place)
```bash
make format
```

##### Build and Publish to PyPI
Building and publishing requires git >= 2.30

Build a wheel and an sdist (tarball) from the package:
```bash
make build
```

Publish to PyPI
```bash
make publish
```
