# Teradata Agents with Flowise AgentFlow and Teradata MCP Server

[![Teradata Data Science Agent](https://img.shields.io/badge/Teradata--Data--Science--Agent-Setup%20Video-green?style=for-the-badge&logo=teradata)](../../docs/media/flowise/GIFs/Teradata_Data_Science_Workflow_Agents_V2.mp4)
[![Teradata Vector Store RAG Agent](https://img.shields.io/badge/Teradata--Vector--Store--Agent-Setup%20Video-green?style=for-the-badge&logo=teradata)](../../docs/media/flowise/GIFs/Teradata%20Vector%20Store%20RAG%20Agent.mp4)
[![Teradata Visualization Agent](https://img.shields.io/badge/Teradata--Visualization--Agent-Template-green?style=for-the-badge&logo=teradata)](./Teradata_visualized_Agents_V2.json)
[![Teradata Customer Lifetime Value (CLV) Demo Agent](https://img.shields.io/badge/Teradata--Customer--Lifetime--Value--Agent--Demo-Setup%20Video-green?style=for-the-badge&logo=teradata)](../../docs/media/flowise/GIFs/Teradata%20Vector%20Store%20RAG%20Agent.mp4)



This repository provides a set of **Teradata Agents** designed to integrate seamlessly with **Flowise AgentFlow** using the **Teradata MCP Server.**
These agents enable intelligent workflows that combine **Teradata’s data and vector capabilities** with **LLM-powered analytics** — helping you build scalable, AI-driven data applications.

Before getting started, make sure both **Teradata MCP Server and Flowise** containers are running as described in the setup guide below.

### 📘 Setup Guide:

Refer to [Flowise_with_Teradata_MCP](../../docs/client_guide/Flowise_with_teradata_mcp_Guide.md)
 for detailed installation and configuration steps.

---

## 🚀 Available Teradata Agents for Flowise

### 🧠 Teradata Data Science Agent

This agent template provides a complete **Flowise workflow** to interact with **Teradata** for data science–related use cases such as querying data, running analytics, and generating insights using LLMs.

#### Template:
[Teradata_Data_Science_Workflow_Agents_V2.json](./Teradata_Data_Science_Workflow_Agents_V2.json)

#### Configuration Steps:

1. Import the JSON template into Flowise.
2. Configure your preferred LLM model and provide its credentials.
3. Save and deploy the workflow.

**🎥 How-To Video**:

Watch this step-by-step video tutorial — [Teradata Data Science Agent Setup](../../docs/media/flowise/GIFs/Teradata_Data_Science_Workflow_Agents_V2.mp4)

---
### 🧩 Teradata Vector Store RAG Agent

This agent template provides a complete **Flowise workflow** to interact with the **Teradata Vector Store**. It supports **similarity search** and **retrieval-augmented generation (RAG) on vectorized data that already resides in Teradata**, enabling context-aware question-answering and semantic insights.

#### Template:
[Teradata_VectorStore_RAG_Agent_V2.json](./Teradata_VectorStore_RAG_Agent_V2.json)

#### Configuration Steps:

1. Import the JSON template into Flowise.
2. Configure your preferred LLM model and provide its credentials.
3. Save and deploy the workflow.

**🎥 How-To Video**:

Watch this step-by-step video tutorial — [Teradata VectorStore RAG Agent Setup](../../docs/media/flowise/GIFs/Teradata%20Vector%20Store%20RAG%20Agent.mp4)

---
### 💼 Customer Lifetime Value (CLV) Demo Agent

This demo agent showcases how **Flowise** and **Teradata MCP Server** can work together to calculate and visualize **Customer Lifetime Value (CLV)** using Teradata data.
It demonstrates practical use of LLMs for analytics, insights generation, and storytelling on customer data.

#### Template:
[Teradata_Customer_Lifetime_Value_V2](./Customer_Lifetime_Value_V2.json)

#### Configuration Steps:

1. Import the JSON template into Flowise.
2. Configure your preferred LLM model and provide its credentials.
3. Save and deploy the workflow.

**🎥 How-To Video**:

Watch this step-by-step video tutorial — [Customer Lifetime Value (CLV) Demo Agent](../../docs/media/flowise/GIFs/Customer_Lifetime_Value_Agent_V2_Demo.mp4)

---
### 📊 Teradata Visualization Agent
This agent template demonstrates how to **visualize Teradata data** within a **Flowise workflow**.
It enables users to generate various types of **plots and charts** (e.g., line, pie, polor, radar) directly from Teradata query results — turning data into interactive visual insights.

#### Template:
[Teradata_visualized_Agents_V2.json](./Teradata_visualized_Agents_V2.json)

#### Configuration Steps:

1. Import the JSON template into Flowise.
2. Configure your preferred LLM model and provide its credentials.
3. Save and deploy the workflow.
