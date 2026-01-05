# Agent-builder

## Purpose

The meta.md file is responsible for building subagent.md files.  It reads any reference documents starting with doc_ and generates <subagent-name>-agent.md file that contains the agent definition and <subagent-name>-spec.md file that contains the requirements for the agent.

The requirements are extracted via a question and answer with the user.

## Usage

1. open a project with claude desktop app
2. Add the meta.md file to the project
3. Add any reference documents starting with doc_ to the project
4. Use extended thinking mode in claude desktop app
5. Use Sonnet or Opus 4.5 models or higher
6. In claude desktop run the meta.md file with a high level scope for the agent.  E.g. "read meta.md and build a subaject that builds and maintains a statistics collection process for a Teradata environment."


## Video example

https://www.youtube.com/watch?v=a4pfse1ZI_c

## Add your agents

Please add your agents you wish to share in the Example-outputs folder, create a subfolder with the agent name and add the generated files there.

## Notes
- this approach should work for other clients and models, it may need some refinement.