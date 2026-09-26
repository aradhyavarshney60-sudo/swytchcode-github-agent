# AI Software Engineer: GitHub Issue Analysis & Automated Reporting

An AI-powered software engineering agent that connects to GitHub, retrieves repository issues, and uses Google Gemini AI to generate clear and structured issue summaries.

## 🚀 Overview

Managing GitHub issues manually can take time, especially when a repository contains multiple issues.

This project automates that process by combining the GitHub API with Google Gemini AI.

The agent:

- Connects to a GitHub repository
- Retrieves open GitHub issues
- Displays issue details such as title, description, and URL
- Sends issue information to Google Gemini
- Generates an AI-powered summary
- Identifies common themes and priorities
- Produces a formatted report directly in the terminal
- Includes fallback handling when API access is unavailable

## ✨ Features

### GitHub Integration
The agent connects to a GitHub repository and retrieves its issues using the GitHub API.

### AI-Powered Analysis
Google Gemini is used to analyze the retrieved issue information and generate a human-readable summary.

### Automated Reporting
The final result is presented as a structured terminal report instead of requiring manual issue-by-issue analysis.

### REST API Fallback
A REST-based fallback is included to improve reliability when the primary GitHub integration is unavailable.

### Sample Mode
The project includes a sample mode that can generate a formatted report using embedded sample issue data when live API access is unavailable.

### Error Handling
The application handles common problems such as:

- Missing GitHub token
- Missing Gemini API key
- GitHub API errors
- Network/API access failures
- User interruption

## 🛠️ Technologies Used

- Python
- GitHub API
- Google Gemini API
- REST API
- PowerShell
- VS Code
- Git & GitHub

## 📁 Project Structure

```text
my-project/
│
├── agent.py
├── issue_payload.json
├── pull_get_info.txt
│
├── .swytchcode/
│   ├── integrations/
│   ├── mcp.pid
│   ├── tooling.json
│   ├── tooling.json.lock
│   └── workspace.json
│
└── .gitignore
