# Solve GitHub Issue

Analyze and solve the GitHub issue: $ARGUMENTS

Follow these steps:

1. **Fetch the issue details** using `gh issue view $ARGUMENTS`
2. **Understand the problem** by reading the issue description and any comments
3. **Search the codebase** to locate relevant files mentioned in the issue
4. **Plan the solution** following the project's coding standards in a TDD approach. Ask user for approval. Once approved add the plan as a comment to the github issue.
5. **Implement the Solution** following the TDD approach in a new github feature development branch. Commit completion of intermediate steps towards the solution.
6. **Ensure high test coverage** to verify the fix works correctly
7. **Run the test suite** with `pytest` to ensure everything (also old tests) passes
8. **Adapt the documentation** if needed
9. **Commit your changes** with a descriptive message referencing the issue number and link to the isse
10. **Comment on the issue** with your implementation approach using `gh issue comment $ARGUMENTS`
11. **Push your changes** to the remote repository
12. **Ensure CI/CD Pipeline** executes successfully
13. **Close the issue** linking to all related commits
14. **Merge with Main** if not already done

When implementing:
- Follow Python best practices: Black formatting, type hints, docstrings
- Ensure comprehensive test coverage for the changed code
- Update documentation if the changes affect user-facing features
- Use conventional commit format: "fix: resolve issue #$ARGUMENTS - [brief description]"
