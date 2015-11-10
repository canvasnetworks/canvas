from distutils.core import setup, Extension

setup(
    name='factlib',
    version='1.0',
    py_modules=['factlib'],
    ext_modules=[
        Extension('_factlib', ['_factlib.c'])
    ]
)
