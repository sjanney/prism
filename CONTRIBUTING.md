# Contributing to Prism 🌈

First off, thank you for considering contributing to Prism! It's people like you that make Prism such a great tool.

## 🚀 How Can I Contribute?

### Reporting Bugs
*   Check the [Issues](https://github.com/sjanney/prism/issues) to see if the bug has already been reported.
*   If not, open a new issue with a clear title and description. Include as much relevant information as possible, such as your OS, Python/Go versions, and a way to reproduce the error.

### Suggesting Enhancements
*   Enhancement suggestions are tracked as [GitHub issues](https://github.com/sjanney/prism/issues).
*   Describe the target use case and why this enhancement would be useful to most Prism users.

### Pull Requests
1.  Fork the repo and create your branch from `main`.
2.  If you've added code that should be tested, add tests.
3.  If you've changed APIs, update the documentation.
4.  Ensure the test suite passes.
5.  Make sure your code lints.

## 🛠 Development Environment

1.  **Backend**: Python 3.9+ with PyTorch.
2.  **Frontend**: Go 1.21+.
3.  **Protos**: We use gRPC. If you change `proto/prism.proto`, run `./codegen.sh`.

```bash
make install
make build
./run_prism.sh
```

## 📜 License
By contributing, you agree that your contributions will be licensed under its Apache 2.0 License.
