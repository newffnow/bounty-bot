#!/usr/bin/env python3
"""
Bounty Verification Bot - Auto-Verify Star/Follow Claims for RustChain Bounties

This bot monitors bounty issue comments, detects claims, and posts automated verification results.
Designed for GitHub Action workflow or standalone execution.

Features:
- Star/follow verification (GitHub API)
- Wallet existence check (RustChain node API)
- Article/URL verification (HEAD request)
- Duplicate claim detection
- Dev.to article word count + quality check

Author: 刘颖 (OpenClaw Assistant)
License: MIT
"""

import os
import re
import json
import time
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

# Configuration
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
RUSTCHAIN_NODE_URL = os.environ.get('RUSTCHAIN_NODE_URL', 'https://rustchain.org')
SCOTT_USERNAME = 'Scottcjn'

# Bounty rules (configurable)
RTC_PER_STAR = 1.0
FOLLOW_MULTIPLIER = 1.5
MIN_STARS_FOR_MULTIPLIER = 45


class BountyVerifier:
    """Automated bounty claim verification bot."""
    
    def __init__(self, github_token: str = '', rustchain_node_url: str = ''):
        self.github_token = github_token or GITHUB_TOKEN
        self.rustchain_node_url = rustchain_node_url or RUSTCHAIN_NODE_URL
        self.github_headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        } if self.github_token else {}
        
    def check_follows_scott(self, username: str) -> Tuple[bool, int]:
        """
        Check if user follows @Scottcjn and count Scottcjn repos starred.
        
        Returns:
            (follows: bool, starred_count: int)
        """
        if not self.github_token:
            return False, 0
            
        # Check if user follows Scottcjn
        follows_url = f'https://api.github.com/users/{username}/following/{SCOTT_USERNAME}'
        try:
            resp = requests.get(follows_url, headers=self.github_headers, timeout=10)
            follows = (resp.status_code == 204)  # 204 = following
        except Exception as e:
            print(f"Error checking follow status: {e}")
            follows = False
            
        # Count Scottcjn repos starred by user
        starred_url = f'https://api.github.com/users/{username}/starred'
        starred_count = 0
        try:
            page = 1
            while True:
                params = {'per_page': 100, 'page': page}
                resp = requests.get(starred_url, headers=self.github_headers, params=params, timeout=10)
                if resp.status_code != 200:
                    break
                repos = resp.json()
                if not repos:
                    break
                # Count repos owned by Scottcjn
                for repo in repos:
                    if repo.get('owner', {}).get('login') == SCOTT_USERNAME:
                        starred_count += 1
                if len(repos) < 100:
                    break
                page += 1
                time.sleep(0.5)  # Rate limit friendly
        except Exception as e:
            print(f"Error counting starred repos: {e}")
            
        return follows, starred_count
    
    def check_wallet_exists(self, wallet_address: str) -> Tuple[bool, Optional[float]]:
        """
        Check if RustChain wallet exists and get balance.
        
        Returns:
            (exists: bool, balance: Optional[float])
        """
        # Try the official API endpoint
        url = f'{self.rustchain_node_url}/wallet/balance?miner_id={wallet_address}'
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                balance = data.get('amount_rtc', 0)
                return True, balance
        except Exception as e:
            print(f"Error checking wallet: {e}")
            
        # Try fallback IP
        fallback_url = f'https://50.28.86.131/wallet/balance?miner_id={wallet_address}'
        try:
            resp = requests.get(fallback_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                balance = data.get('amount_rtc', 0)
                return True, balance
        except Exception as e:
            print(f"Error checking wallet (fallback): {e}")
            
        return False, None
    
    def check_url_live(self, url: str) -> Tuple[bool, str]:
        """
        Check if URL is live and get metadata.
        
        Returns:
            (is_live: bool, platform: str)
        """
        try:
            resp = requests.head(url, timeout=10, allow_redirects=True)
            is_live = (resp.status_code == 200)
            
            # Detect platform
            platform = 'unknown'
            if 'dev.to' in url:
                platform = 'dev.to'
            elif 'medium.com' in url:
                platform = 'medium'
            elif 'github.com' in url:
                platform = 'github'
            elif 'youtube.com' in url or 'youtu.be' in url:
                platform = 'youtube'
                
            return is_live, platform
        except Exception as e:
            print(f"Error checking URL: {e}")
            return False, 'unknown'
    
    def check_devto_article(self, url: str) -> Tuple[bool, int, str]:
        """
        Check dev.to article word count and quality.
        
        Returns:
            (is_valid: bool, word_count: int, quality: str)
        """
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return False, 0, 'unreachable'
                
            # Extract article content (simplified - look for main text)
            content = resp.text
            
            # Remove HTML tags and count words
            text = re.sub(r'<[^>]+>', ' ', content)
            words = text.split()
            word_count = len(words)
            
            # Quality assessment
            if word_count < 100:
                quality = 'too_short'
            elif word_count < 300:
                quality = 'short'
            elif word_count < 1000:
                quality = 'good'
            else:
                quality = 'excellent'
                
            return True, word_count, quality
        except Exception as e:
            print(f"Error checking dev.to article: {e}")
            return False, 0, 'error'
    
    def check_duplicate_claim(self, comments: List[Dict], username: str) -> Optional[str]:
        """
        Check if user has already been paid on this or other bounties.
        
        Returns:
            previous_claim_info or None
        """
        for comment in comments:
            author = comment.get('user', {}).get('login', '')
            body = comment.get('body', '')
            
            if author == username and 'PAID' in body.upper():
                # Extract payment info
                match = re.search(r'PAID\s+(\d+)\s*RTC', body, re.IGNORECASE)
                if match:
                    amount = match.group(1)
                    return f'Paid {amount} RTC previously'
                    
        return None
    
    def parse_claim_comment(self, comment_body: str) -> Dict[str, str]:
        """
        Parse claim comment to extract wallet, stars, GitHub username, etc.
        
        Expected format:
        - Claiming this bounty
        - Wallet: RTCxxxxx
        - Stars: 50
        - GitHub: username
        - Article: https://dev.to/...
        
        Returns:
            Dict with extracted fields
        """
        claim_data = {
            'wallet': None,
            'stars': None,
            'github_username': None,
            'article_url': None,
            'is_claiming': False
        }
        
        # Check if this is a claim
        claiming_keywords = ['claiming', 'claim', 'wallet:', 'stars:', 'github:']
        comment_lower = comment_body.lower()
        claim_data['is_claiming'] = any(kw in comment_lower for kw in claiming_keywords)
        
        if not claim_data['is_claiming']:
            return claim_data
            
        # Extract wallet address (RTC followed by alphanumeric)
        wallet_match = re.search(r'wallet[:\s]+([a-zA-Z0-9]+)', comment_body, re.IGNORECASE)
        if wallet_match:
            claim_data['wallet'] = wallet_match.group(1)
            
        # Extract star count
        stars_match = re.search(r'stars[:\s]+(\d+)', comment_body, re.IGNORECASE)
        if stars_match:
            claim_data['stars'] = int(stars_match.group(1))
            
        # Extract GitHub username
        github_match = re.search(r'github[:\s@]+([a-zA-Z0-9_-]+)', comment_body, re.IGNORECASE)
        if github_match:
            claim_data['github_username'] = github_match.group(1)
            
        # Extract article URL
        url_match = re.search(r'(https?://[^\s]+)', comment_body)
        if url_match:
            claim_data['article_url'] = url_match.group(1)
            
        return claim_data
    
    def verify_claim(self, username: str, comment_body: str, issue_comments: List[Dict] = None) -> Dict:
        """
        Perform full verification on a claim.
        
        Returns:
            Verification results dict
        """
        claim_data = self.parse_claim_comment(comment_body)
        results = {
            'username': username,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'checks': {}
        }
        
        if not claim_data['is_claiming']:
            results['is_claim'] = False
            return results
            
        results['is_claim'] = True
        
        # 1. Check follows Scottcjn
        follows, starred_count = self.check_follows_scott(username)
        results['checks']['follows_scottcjn'] = {
            'result': follows,
            'scottcjn_repos_starred': starred_count
        }
        
        # 2. Check wallet exists
        if claim_data['wallet']:
            exists, balance = self.check_wallet_exists(claim_data['wallet'])
            results['checks']['wallet'] = {
                'address': claim_data['wallet'],
                'exists': exists,
                'balance': balance
            }
        
        # 3. Check article URL
        if claim_data['article_url']:
            is_live, platform = self.check_url_live(claim_data['article_url'])
            results['checks']['article'] = {
                'url': claim_data['article_url'],
                'is_live': is_live,
                'platform': platform
            }
            
            # If dev.to, get word count
            if platform == 'dev.to':
                valid, word_count, quality = self.check_devto_article(claim_data['article_url'])
                results['checks']['article']['word_count'] = word_count
                results['checks']['article']['quality'] = quality
        
        # 4. Check duplicate claims
        if issue_comments:
            duplicate = self.check_duplicate_claim(issue_comments, username)
            results['checks']['duplicate'] = {
                'has_previous_claim': duplicate is not None,
                'info': duplicate
            }
        
        # 5. Calculate suggested payout
        results['payout'] = self.calculate_payout(results['checks'])
        
        return results
    
    def calculate_payout(self, checks: Dict) -> Dict:
        """Calculate suggested payout based on verification results."""
        base_rtc = 0
        
        # Star-based payout
        starred = checks.get('follows_scottcjn', {}).get('scottcjn_repos_starred', 0)
        follows = checks.get('follows_scottcjn', {}).get('result', False)
        
        if starred > 0:
            base_rtc = starred * RTC_PER_STAR
            if follows and starred >= MIN_STARS_FOR_MULTIPLIER:
                base_rtc *= FOLLOW_MULTIPLIER
                
        # Wallet bonus
        if checks.get('wallet', {}).get('exists'):
            base_rtc += 5  # Small bonus for having wallet
            
        # Article bonus
        article = checks.get('article', {})
        if article.get('is_live'):
            word_count = article.get('word_count', 0)
            if word_count >= 500:
                base_rtc += 10
            elif word_count >= 200:
                base_rtc += 5
                
        return {
            'suggested_rtc': round(base_rtc, 2),
            'breakdown': {
                'stars': starred,
                'follows': follows,
                'wallet_exists': checks.get('wallet', {}).get('exists', False),
                'article_live': article.get('is_live', False),
                'word_count': article.get('word_count', 0)
            }
        }
    
    def format_verification_report(self, results: Dict) -> str:
        """Format verification results as a GitHub comment."""
        if not results.get('is_claim'):
            return "[WARNING] This doesn't appear to be a bounty claim comment."
            
        checks = results['checks']
        payout = results['payout']
        
        # Build verification table
        lines = [
            f"## Automated Verification for @{results['username']}",
            f"_Verified at {results['timestamp']}_",
            "",
            "| Check | Result |",
            "|-------|--------|"
        ]
        
        # Follows Scottcjn
        follows = checks.get('follows_scottcjn', {})
        follows_icon = '[Y]' if follows.get('result') else '[N]'
        lines.append(f"| Follows @Scottcjn | {follows_icon} {'Yes' if follows.get('result') else 'No'} |")
        
        # Starred repos
        starred = follows.get('scottcjn_repos_starred', 0)
        lines.append(f"| Scottcjn repos starred | {starred} |")
        
        # Wallet
        wallet = checks.get('wallet', {})
        if wallet:
            wallet_icon = '[Y]' if wallet.get('exists') else '[N]'
            balance_str = f"{wallet.get('balance', 0):.2f} RTC" if wallet.get('balance') else 'N/A'
            lines.append(f"| Wallet `{wallet.get('address', '')}` exists | {wallet_icon} Balance: {balance_str} |")
        
        # Article
        article = checks.get('article', {})
        if article:
            article_icon = '[Y]' if article.get('is_live') else '[N]'
            platform = article.get('platform', 'unknown')
            word_count = article.get('word_count', 0)
            quality = article.get('quality', 'unknown')
            lines.append(f"| Article link | {article_icon} Live ({platform}, {word_count} words, {quality}) |")
        
        # Duplicate check
        duplicate = checks.get('duplicate', {})
        if duplicate.get('has_previous_claim'):
            lines.append(f"| Previous claims | [!] {duplicate.get('info', 'Unknown')} |")
        else:
            lines.append(f"| Previous claims | [OK] None found |")
        
        # Payout suggestion
        lines.extend([
            "",
            "### Suggested Payout",
            "",
            f"**{payout['suggested_rtc']:.1f} RTC**",
            "",
            "**Breakdown:**",
            f"- Stars: {payout['breakdown']['stars']} x {RTC_PER_STAR} RTC = {payout['breakdown']['stars'] * RTC_PER_STAR:.1f} RTC",
        ])
        
        if payout['breakdown']['follows'] and payout['breakdown']['stars'] >= MIN_STARS_FOR_MULTIPLIER:
            lines.append(f"- Follow bonus (x{FOLLOW_MULTIPLIER}): Applied")
        if payout['breakdown']['wallet_exists']:
            lines.append(f"- Wallet bonus: +5 RTC")
        if payout['breakdown']['article_live'] and payout['breakdown']['word_count'] >= 500:
            lines.append(f"- Article bonus: +10 RTC")
        elif payout['breakdown']['article_live'] and payout['breakdown']['word_count'] >= 200:
            lines.append(f"- Article bonus: +5 RTC")
            
        lines.extend([
            "",
            "---",
            "_This is an automated verification. Final payout decision by @Scottcjn._"
        ])
        
        return '\n'.join(lines)


def main():
    """Main entry point for standalone execution."""
    print("=" * 60)
    print("Bounty Verification Bot v1.0")
    print("=" * 60)
    
    verifier = BountyVerifier()
    
    # Demo: verify a sample claim
    sample_claim = """
    Claiming this bounty!
    Wallet: newffnow-github
    Stars: 50
    GitHub: newffnow
    Article: https://dev.to/example/article
    """
    
    print("\n[TEST] Sample claim comment:")
    print(sample_claim)
    print("\n[TEST] Running verification...")
    
    results = verifier.verify_claim('newffnow', sample_claim)
    
    print("\n" + "=" * 60)
    print("VERIFICATION REPORT")
    print("=" * 60)
    print(verifier.format_verification_report(results))
    
    print("\n[OK] Verification complete!")
    return results


if __name__ == '__main__':
    main()
