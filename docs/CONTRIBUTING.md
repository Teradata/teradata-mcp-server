# Contributing Guidelines
Make sure you have setup your environment based on the Developer Guide in this repo. The goal is to allow contributions to this project by anyone, and that all code requirements are automated. Here are the guidelines we adhere to as a team.

## Development Guidelines
- Always engage on the discussion board or create an issue before creating a PR. 
- All PRs must have at least one issue associated.
- Run testing before PR, and copy/paste the test report status in the PR. You can simply run the mandatory test tools with `python tests/run_mcp_tests.py "uv run teradata-mcp-server"`. For more information see [our testing guide](/tests/README.md)
- Create a new test case if you add a new tool. For more information see [our testing guide](/tests/README.md)
- All code must be reviewed via a pull request. Before anything can be merged, it must be reviewed by at least 2 others. [Contributing to a project step by step instuctions](https://docs.github.com/en/get-started/exploring-projects-on-github/contributing-to-a-project)
- Squash commits into a single commit for your PR. We want to keep a clean git history.
- Code should adhere to lint and codestyle tests. While you can commit code that doesn't validate but still works, it is encouraged to validate your code. It saves other's headaches down the road.
- Code must pass existing tests when submitting a pull request. If your code breaks a test, it needs to be updated to pass the tests before merging.
- New code should come with proper tests. Your code should come with proper test coverage, ideally 95+%, minimum 80%, before it can be merged.
- Bug fixes must come with a test. Any bug fixes should come with an appropriate test to verify the bug is fixed, and does not return.
- Code structure should be maintained. The structure of the repo and files has been carefully crafted, and any deviations from that should be only done when agreed upon by the entire team.

## Design Guidelines
- Refer to [Developer Guide](./developer_guide/DEVELOPER_GUIDE.md).
