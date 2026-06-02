# Churn Prevention Agent

An AI agent that detects early customer churn signals in SAP S/4HANA, scores at-risk accounts, and surfaces personalised Joule alerts to sales teams with full GDPR audit trail logging.

## Overview

Uses A2A Protocol, LangGraph, LiteLLM, and SAP Cloud SDK.

## Structure

- `app/main.py` - A2A server entry
- `app/agent_executor.py` - Request handling
- `app/agent.py` - Agent logic
