#!/usr/bin/env node
/**
 * create-burner-ig.js — Create Instagram burner account via stealth Chrome + guerrilla mail
 *
 * Usage:
 *   node create-burner-ig.js
 *
 * Output: Session cookies saved to ~/.hermes/state/instagram-cookies.json
 */

const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const https = require('https');
const fs = require('fs');
const path = require('path');

puppeteer.use(StealthPlugin());

const GUERRILLA_BASE = 'https://api.guerrillamail.com/ajax.php';
const COOKIES_FILE = path.join(process.env.HOME, '.hermes', 'state', 'instagram-cookies.json');

function guerrillaRequest(params) {
  return new Promise((resolve, reject) => {
    const qs = Object.entries(params).map(([k,v]) => `${k}=${encodeURIComponent(v)}`).join('&');
    const url = `${GUERRILLA_BASE}?${qs}`;
    https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' } }, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch(e) { reject(e); }
      });
    }).on('error', reject);
  });
}

async function waitForEmail(sidToken, timeoutMs = 120000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const result = await guerrillaRequest({
      f: 'fetch_email',
      sid_token: sidToken,
    });
    if (result.list && result.list.length > 0) {
      return result.list[0];
    }
    await new Promise(r => setTimeout(r, 3000));
  }
  return null;
}

function extractCode(emailBody) {
  // Instagram sends a 6-digit code
  const match = emailBody.match(/\b(\d{6})\b/);
  return match ? match[1] : null;
}

async function main() {
  console.log('=== Creating Instagram Burner Account ===\n');

  // Step 1: Get temp email
  console.log('1. Getting temp email...');
  const emailResult = await guerrillaRequest({
    f: 'get_email_address',
    ip: '127.0.0.1',
    agent: 'Mozilla_5_0',
  });
  const email = emailResult.email_addr;
  const sidToken = emailResult.sid_token;
  console.log(`   Email: ${email}`);

  // Step 2: Launch stealth browser
  console.log('2. Launching stealth browser...');
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 900 });
  await page.setUserAgent(
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36'
  );

  // Step 3: Navigate to Instagram signup
  console.log('3. Navigating to Instagram signup...');
  await page.goto('https://www.instagram.com/accounts/emailsignup/', {
    waitUntil: 'networkidle2',
    timeout: 30000,
  });
  await new Promise(r => setTimeout(r, 2000));

  // Step 4: Fill signup form
  console.log('4. Filling signup form...');
  
  // Instagram signup uses these fields
  const emailInput = await page.$('input[name="emailOrPhone"]');
  const fullNameInput = await page.$('input[name="fullName"]');
  const usernameInput = await page.$('input[name="username"]');
  const passwordInput = await page.$('input[name="password"]');

  if (!emailInput || !fullNameInput || !usernameInput || !passwordInput) {
    console.log('   Form fields not found — page might have changed. Taking screenshot...');
    await page.screenshot({ path: '/tmp/ig-signup-debug.png' });
    console.log('   Screenshot saved to /tmp/ig-signup-debug.png');
    await browser.close();
    process.exit(1);
  }

  const username = `trailhead_research_${Date.now().toString(36)}`;
  await emailInput.type(email);
  await fullNameInput.type('Trailhead Research');
  await usernameInput.type(username);
  await passwordInput.type('Tr4!lh34dR3s34rch!!99');

  console.log(`   Username: ${username}`);

  // Step 5: Submit
  console.log('5. Submitting form...');
  const submitBtn = await page.$('button[type="submit"]');
  if (submitBtn) {
    await submitBtn.click();
  } else {
    // Try pressing Enter on password field
    await passwordInput.press('Enter');
  }
  
  await new Promise(r => setTimeout(r, 5000));

  // Step 6: Check if we need to enter confirmation code
  console.log('6. Checking for confirmation code prompt...');
  
  const pageText = await page.evaluate(() => document.body.textContent);
  
  if (pageText.includes('confirmation code') || pageText.includes('Enter Confirmation Code')) {
    console.log('   Confirmation code required. Checking email...');
    
    const emailData = await waitForEmail(sidToken, 120000);
    if (!emailData) {
      console.log('   No confirmation email received within 2 minutes.');
      await browser.close();
      process.exit(1);
    }
    
    const code = extractCode(emailData.mail_body || emailData.mail_excerpt || '');
    if (!code) {
      console.log(`   Could not extract code from email: ${emailData.mail_excerpt?.slice(0,200)}`);
      await browser.close();
      process.exit(1);
    }
    
    console.log(`   Got code: ${code}`);
    
    // Enter the code
    const codeInput = await page.$('input[name="email_confirmation_code"]');
    if (codeInput) {
      await codeInput.type(code);
      const confirmBtn = await page.$('button[type="submit"]');
      if (confirmBtn) await confirmBtn.click();
      await new Promise(r => setTimeout(r, 5000));
    }
  } else if (pageText.includes('birthday') || pageText.includes('Birthday')) {
    console.log('   Birthday prompt detected. Filling...');
    // Instagram might ask for birthday
    // Try to fill and continue
  }

  // Step 7: Wait for redirect to home
  console.log('7. Waiting for home page...');
  await new Promise(r => setTimeout(r, 5000));
  
  const currentUrl = page.url();
  console.log(`   Current URL: ${currentUrl}`);

  // Step 8: Export cookies
  console.log('8. Exporting cookies...');
  const cookies = await page.cookies();
  
  fs.mkdirSync(path.dirname(COOKIES_FILE), { recursive: true });
  fs.writeFileSync(COOKIES_FILE, JSON.stringify(cookies, null, 2));
  console.log(`   Saved ${cookies.length} cookies to ${COOKIES_FILE}`);

  // Verify: try to access own profile
  const pageContent = await page.evaluate(() => document.body.textContent.slice(0, 500));
  const loggedIn = !pageContent.includes('Log in') && !pageContent.includes('Sign up');
  console.log(`   Logged in: ${loggedIn}`);

  await browser.close();
  console.log('\n=== DONE ===');
}

main().catch(e => {
  console.error('FATAL:', e.message);
  process.exit(1);
});
