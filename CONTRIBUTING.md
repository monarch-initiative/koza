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

Build a wheel and an sdist (tarball) from the package:
```bash
make build
```

Publish to PyPI
```bash
make publish
```