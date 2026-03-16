#!/usr/bin/env python3
"""
GitHub Action script to verify bounty claims and post results.

This script is called by the GitHub Action workflow and:
1. Imports the BountyVerifier class
2. Verifies the claim from the comment
3. Outputs the verification report as an environment variable
"""

import os
import sys
import argparse
import json

# Add parent directory to path to import bounty_verifier
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bounty_verifier import BountyVerifier


def main():
    parser = argparse.ArgumentParser(description='Verify bounty claim')
    parser.add_argument('--issue-number', type=int, required=True)
    parser.add_argument('--comment-id', type=int, required=True)
    parser.add_argument('--username', type=str, required=True)
    parser.add_argument('--comment-body', type=str, required=True)
    args = parser.parse_args()
    
    print(f"Verifying claim from @{args.username} on issue #{args.issue_number}")
    
    # Initialize verifier
    verifier = BountyVerifier(
        github_token=os.environ.get('GITHUB_TOKEN', ''),
        rustchain_node_url=os.environ.get('RUSTCHAIN_NODE_URL', 'https://rustchain.org')
    )
    
    # Verify the claim
    results = verifier.verify_claim(args.username, args.comment_body)
    
    # Format the report
    report = verifier.format_verification_report(results)
    
    # Output as environment variable for the next step
    # Note: In real GitHub Action, we'd use GitHub Actions output or write to a file
    print("\n" + "=" * 60)
    print("VERIFICATION REPORT")
    print("=" * 60)
    print(report)
    
    # Write report to file for GitHub Action to read
    with open('/tmp/verification_report.md', 'w') as f:
        f.write(report)
    
    # Set output for GitHub Actions
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"VERIFICATION_REPORT<<EOF\n{report}\nEOF\n")
    
    print("\n✅ Verification complete!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
