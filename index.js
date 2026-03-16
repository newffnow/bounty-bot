const core = require('@actions/core');
const github = require('@actions/github');

async function run() {
  try {
    const token = core.getInput('github-token', { required: true });
    const rustchainNodeUrl = core.getInput('rustchain-node-url') || 'https://50.28.86.131';
    const followRequired = core.getInput('follow-required') !== 'false';
    const minStars = parseInt(core.getInput('min-stars')) || 0;
    const rtcPerStar = parseFloat(core.getInput('rtc-per-star')) || 1.0;
    const followMultiplier = parseFloat(core.getInput('follow-multiplier')) || 1.0;

    const octokit = github.getOctokit(token);
    const context = github.context;

    // Only run on issue comments
    if (context.eventName !== 'issue_comment') {
      console.log('Skipping: not an issue_comment event');
      return;
    }

    const comment = context.payload.comment;
    const commentBody = comment.body.toLowerCase();
    const issue = context.payload.issue;

    // Check if this is a claim (look for keywords)
    const claimKeywords = ['claiming', 'claim', 'wallet:', 'stars:', 'github:'];
    const isClaim = claimKeywords.some(keyword => commentBody.includes(keyword));

    if (!isClaim) {
      console.log('Skipping: not a claim comment');
      return;
    }

    console.log(`Processing claim from @${comment.user.login} on issue #${issue.number}`);

    const claimant = comment.user.login;
    
    // Extract wallet address from comment (look for patterns like "wallet: XYZ" or "RTC...")
    const walletMatch = comment.body.match(/wallet[:\s]*([A-Za-z0-9]+)/i) || 
                        comment.body.match(/(RTC[A-Za-z0-9]{30,})/i);
    const walletAddress = walletMatch ? walletMatch[1] : null;

    // Extract star count if mentioned
    const starsMatch = comment.body.match(/stars[:\s]*(\d+)/i);
    const claimedStars = starsMatch ? parseInt(starsMatch[1]) : null;

    // Perform verifications
    const results = {
      follows: null,
      stars: null,
      wallet: null,
      article: null,
      previousClaims: null
    };

    // 1. Check if user follows @Scottcjn
    if (followRequired) {
      try {
        await octokit.rest.users.checkFollowingForUser({
          username: 'Scottcjn',
          target_user: claimant
        });
        results.follows = true;
        console.log(`✓ @${claimant} follows @Scottcjn`);
      } catch (error) {
        if (error.status === 404) {
          results.follows = false;
          console.log(`✗ @${claimant} does NOT follow @Scottcjn`);
        } else {
          console.error('Error checking follow:', error);
          results.follows = 'error';
        }
      }
    }

    // 2. Count stars on Scottcjn repos
    try {
      let starCount = 0;
      let page = 1;
      
      while (true) {
        const { data: starred } = await octokit.rest.activity.listReposStarredByUser({
          username: claimant,
          per_page: 100,
          page: page
        });
        
        const scottStars = starred.filter(repo => repo.owner.login === 'Scottcjn');
        starCount += scottStars.length;
        
        if (starred.length < 100) break;
        page++;
        
        // Safety limit
        if (page > 10) break;
      }
      
      results.stars = starCount;
      console.log(`✓ @${claimant} has starred ${starCount} Scottcjn repos`);
    } catch (error) {
      console.error('Error counting stars:', error);
      results.stars = 'error';
    }

    // 3. Check wallet existence
    if (walletAddress) {
      try {
        const response = await fetch(`${rustchainNodeUrl}/wallet/balance?miner_id=${walletAddress}`);
        if (response.ok) {
          const data = await response.json();
          results.wallet = {
            exists: true,
            balance: data.amount_rtc || data.balance || 'unknown'
          };
          console.log(`✓ Wallet ${walletAddress} exists with balance ${results.wallet.balance} RTC`);
        } else {
          results.wallet = { exists: false };
          console.log(`✗ Wallet ${walletAddress} not found`);
        }
      } catch (error) {
        console.error('Error checking wallet:', error);
        results.wallet = { exists: 'error' };
      }
    }

    // 4. Check for article URLs and verify they're live
    const urlMatches = comment.body.match(/https?:\/\/[^\s<>"{}|\\^`\[\]]+/gi) || [];
    const articleUrls = urlMatches.filter(url => 
      url.includes('dev.to') || url.includes('medium.com') || url.includes('github.com')
    );

    if (articleUrls.length > 0) {
      results.article = [];
      for (const url of articleUrls) {
        try {
          const response = await fetch(url, { method: 'HEAD' });
          results.article.push({
            url: url,
            live: response.ok,
            status: response.status
          });
          console.log(`✓ Article ${url} is live (${response.status})`);
        } catch (error) {
          results.article.push({
            url: url,
            live: false,
            error: error.message
          });
        }
      }
    }

    // 5. Check for previous claims/paid status
    try {
      const { data: comments } = await octokit.rest.issues.listComments({
        owner: context.repo.owner,
        repo: context.repo.repo,
        issue_number: issue.number,
        per_page: 100
      });

      const previousClaims = comments
        .filter(c => c.user.login === claimant && c.id !== comment.id)
        .filter(c => c.body.toLowerCase().includes('paid') || c.body.toLowerCase().includes('claim'));
      
      results.previousClaims = previousClaims.length;
      console.log(`@${claimant} has ${previousClaims.length} previous claims on this issue`);
    } catch (error) {
      console.error('Error checking previous claims:', error);
      results.previousClaims = 'unknown';
    }

    // Calculate suggested payout
    let suggestedPayout = 0;
    if (typeof results.stars === 'number') {
      suggestedPayout = results.stars * rtcPerStar;
      if (results.follows === true) {
        suggestedPayout *= followMultiplier;
      }
    }

    // Build verification comment
    const verificationComment = buildVerificationComment(claimant, results, suggestedPayout, walletAddress);

    // Post the verification comment
    await octokit.rest.issues.createComment({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: issue.number,
      body: verificationComment
    });

    console.log('✓ Verification comment posted');

  } catch (error) {
    core.setFailed(`Bounty verification failed: ${error.message}`);
    console.error(error);
  }
}

function buildVerificationComment(claimant, results, suggestedPayout, walletAddress) {
  const followStatus = results.follows === true ? '✅ Yes' : 
                       results.follows === false ? '❌ No' : '⚠️ Error';
  
  const starsStatus = typeof results.stars === 'number' ? `${results.stars}` : '⚠️ Error';
  
  const walletStatus = results.wallet?.exists === true ? `✅ Balance: ${results.wallet.balance} RTC` :
                       results.wallet?.exists === false ? '❌ Not found' :
                       results.wallet?.exists === 'error' ? '⚠️ Error' : '⚪ Not provided';
  
  let articleStatus = '⚪ No articles';
  if (results.article && results.article.length > 0) {
    const liveCount = results.article.filter(a => a.live === true).length;
    articleStatus = `${liveCount}/${results.article.length} live`;
  }

  const previousClaimsStatus = results.previousClaims === 'unknown' ? '⚠️ Unknown' :
                               results.previousClaims > 0 ? `⚠️ ${results.previousClaims} previous` : '✅ None';

  return `## 🤖 Automated Verification for @${claimant}

| Check | Result |
|-------|--------|
| Follows @Scottcjn | ${followStatus} |
| Scottcjn repos starred | ${starsStatus} |
| Wallet \`${walletAddress || 'N/A'}\` | ${walletStatus} |
| Article links | ${articleStatus} |
| Previous claims | ${previousClaimsStatus} |

**💰 Suggested payout**: ${suggestedPayout > 0 ? `${suggestedPayout.toFixed(1)} RTC` : 'Manual review required'}

---
*Verified by Bounty Bot v1.0 | [Report issues](https://github.com/Scottcjn/rustchain-bounties/issues/new)*`;
}

run();
