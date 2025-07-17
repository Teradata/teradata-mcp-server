## Using with Microsoft Copilot

Developing a Copilot Agent leveraging the Teradata MCP server leveraged [Microsoft Copilot Studio ](https://copilotstudio.microsoft.com/).

Step 1 - Create a new agent

It is possible to have copilot help build the agent, or you can click to configure the agent yourself.
- Give your agent a name:  TD_MCP_Agent
- Fill out the agent description: 
- Provide instructions, this is effectivly a system prompt for the agent.
- click on create

Step 2 - configuring agent LLM
You are able to refine the LLM for the agent by clicking of the ... in the response model section and selecting edit. Select:
- Yes - Responses will be dynamic, using available tools and knowledge as appropriate
- in the Knowledge section turn off "Use general knowledge" and "Use information from the web", as these will reduce the impact of the MCP data
- click on Save, close the LLM setting by clicking on X

Step 3 - Create the connection to the MCP server
- Click on the Tools tab. 
- Click on add tool
- Click on Model Context Protocol, if the server has already been set up you will find it in this list and go to step 5, if not step 4 will be required


Step 4 - configure the connection
- Click on New Tool if the server has not been set up
- Click on Module Context Protocol for istructions, it will tell you to click on Custom Connector which will open power apps
- Click on New custom connector, selecting "Inpit OpenAPI File"
- Give you connector a name and import [copilot_swagger.yaml](/test/Copilot_Agent/copilot_swagger.yaml)
- click on Continue
- Define the schema, Http or https, this will be determined by how you set up the server.
- Define the Host, this needs to be an IP that it routable from the cloud.  We have used IP forwarding on a small cloud based server to connect to a on-premise MCP server as an example.
- the base URL will be /, it will add mcp itself.
- go to Security
- security would need to be added if using Oauth
- go to Definition
- toggle the Swagger editor, this will allow you to see the swagger file we imported.
- modify the host
- click on Create connector

Step 5 - add the server to the agent
- Click on Add to agent

Step 6 - test the agent
- Ask the agent "what databases do I have"
- the first time you do you will need to click on Open connection manager, this will open a new tab in your browser 
- click on Connect for your Server
- click on Submit to start the connection to your server
- Go back to the Agent tab in your browser and retry your query, you should now have the agent connected to the MCP server

Step 7 - deploying your agent

Once the agent is complete you can publish your agent.

