# Geopolitical Risk Intelligence Agent

An AI agent that monitors real-time geopolitical events from GDELT, correlates conflict signals with SAP supplier and purchase order data, scores risk severity, creates SAP workflow tasks, updates supplier risk profiles, and dispatches alerts.

## Overview

Uses A2A Protocol, LangGraph, LiteLLM, and SAP Cloud SDK.

## Structure

- `app/main.py` - A2A server entry
- `app/agent_executor.py` - Request handling
- `app/agent.py` - Agent logic
