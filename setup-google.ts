import { OAuth2Client } from 'google-auth-library';
import * as readline from 'readline';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Check if required environment variables are set
if (!process.env.GOOGLE_CLIENT_ID || !process.env.GOOGLE_CLIENT_SECRET) {
    console.error('Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env file');
    process.exit(1);
}

// Define the required scopes
const SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive.file'
];

// Create OAuth2 client
const oauth2Client = new OAuth2Client(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    'http://localhost:3000/auth/google/callback'
);

// Generate authentication URL
const authUrl = oauth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: SCOPES,
    prompt: 'consent'
});

console.log('\n=== Google OAuth Setup ===\n');
console.log('1. Visit this URL in your browser to authorize the application:');
console.log('\n' + authUrl + '\n');
console.log('2. After authorization, you will be redirected to a page that might show an error (this is expected)');
console.log('3. Copy the "code" parameter from the URL of that page');
console.log('   (It will be after "code=" and before "&" or end of URL)\n');

// Create readline interface for user input
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
});

// Get the authorization code from user
rl.question('Enter the code here: ', async (code) => {
    try {
        console.log('\nGetting tokens...');
        const { tokens } = await oauth2Client.getToken(code);

        console.log('\n=== Success! ===\n');
        console.log('Add these tokens to your .env file:\n');
        console.log(`GOOGLE_ACCESS_TOKEN=${tokens.access_token}`);
        console.log(`GOOGLE_REFRESH_TOKEN=${tokens.refresh_token}\n`);

        console.log('After adding these to your .env file, restart your application.\n');
    } catch (error) {
        console.error('\nError getting tokens:', error instanceof Error ? error.message : 'Unknown error');
        console.log('\nPlease try again and make sure you copy the entire code from the URL.');
    } finally {
        rl.close();
    }
}); 