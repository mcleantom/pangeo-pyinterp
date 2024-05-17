# Pyinterp

This is a clone of the [pangeo-pyinterp](https://github.com/CNES/pangeo-pyinterp) library, however it has been refactored to use vcpkg to manage its dependencies,
and to use scikit-build-core to build the python bindings. Ensure to clone the repository with the `--recursive` flag to get the submodules.

```bash
git clone --recursive
```

## Windows

Then initialize vcpkg by running:

```bash
./initialize-repo.bat
```

Wheels for the library can be created by running:

```bash
./build-wheels.bat
```