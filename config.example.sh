#!/usr/bin/env bash
# InvestAgents configuration
# Source this file before running:  source config.sh
#
# Copy to config.sh and fill in your keys:
#   cp config.example.sh config.sh

# LLM Provider (deepseek, openai, anthropic, google)
export INVESTAGENTS_LLM_PROVIDER=deepseek
export INVESTAGENTS_DEEP_MODEL=deepseek-chat        # model for thesis/portfolio
export INVESTAGENTS_QUICK_MODEL=deepseek-chat       # model for analyst reports

# LLM API Keys (set at least one)
export DEEPSEEK_API_KEY=sk-your-key-here
# export OPENAI_API_KEY=sk-your-key-here
# export ANTHROPIC_API_KEY=sk-your-key-here
# export GOOGLE_API_KEY=your-key-here

# Optional: FRED macro data (free from https://fred.stlouisfed.org)
export FRED_API_KEY=your-fred-key-here

# Analysis settings
export INVESTAGENTS_DEBATE_ROUNDS=0                 # 0=fast, 1=standard, 2=deep
export INVESTAGENTS_OUTPUT_LANGUAGE=Vietnamese       # or English, Japanese, etc.
