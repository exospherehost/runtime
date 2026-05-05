#!/usr/bin/env node

/**
 * Version management script for the TypeScript SDK
 * 
 * Usage:
 *   node scripts/version.js beta    # Create beta version (0.1.0b1)
 *   node scripts/version.js patch   # Create patch version (0.1.1)
 *   node scripts/version.js minor   # Create minor version (0.2.0)
 *   node scripts/version.js major   # Create major version (1.0.0)
 */

import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const packageJsonPath = path.join(__dirname, '..', 'package.json');
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));

function getCurrentVersion() {
  return packageJson.version;
}

function updateVersion(type) {
  const currentVersion = getCurrentVersion();
  console.log(`Current version: ${currentVersion}`);
  
  let newVersion;
  
  switch (type) {
    case 'beta':
      // If current version already has beta, increment beta number
      if (currentVersion.includes('b')) {
        const [baseVersion, betaNum] = currentVersion.split('b');
        newVersion = `${baseVersion}b${parseInt(betaNum) + 1}`;
      } else {
        // Create first beta version
        newVersion = `${currentVersion}b1`;
      }
      break;
      
    case 'patch':
      if (currentVersion.includes('b')) {
        // Remove beta suffix for stable release
        newVersion = currentVersion.split('b')[0];
      } else {
        // Increment patch version
        const [major, minor, patch] = currentVersion.split('.').map(Number);
        newVersion = `${major}.${minor}.${patch + 1}`;
      }
      break;
      
    case 'minor':
      if (currentVersion.includes('b')) {
        // Remove beta suffix and increment minor
        const [major, minor] = currentVersion.split('b')[0].split('.').map(Number);
        newVersion = `${major}.${minor + 1}.0`;
      } else {
        // Increment minor version
        const [major, minor] = currentVersion.split('.').map(Number);
        newVersion = `${major}.${minor + 1}.0`;
      }
      break;
      
    case 'major':
      if (currentVersion.includes('b')) {
        // Remove beta suffix and increment major
        const major = parseInt(currentVersion.split('b')[0].split('.')[0]) + 1;
        newVersion = `${major}.0.0`;
      } else {
        // Increment major version
        const major = parseInt(currentVersion.split('.')[0]) + 1;
        newVersion = `${major}.0.0`;
      }
      break;
      
    default:
      console.error(`Unknown version type: ${type}`);
      console.error('Valid types: beta, patch, minor, major');
      process.exit(1);
  }
  
  console.log(`New version: ${newVersion}`);
  
  // Update package.json
  packageJson.version = newVersion;
  fs.writeFileSync(packageJsonPath, JSON.stringify(packageJson, null, 2) + '\n');
  
  console.log(`✅ Updated package.json to version ${newVersion}`);
  
  // Show next steps
  console.log('\n📋 Next steps:');
  console.log('1. Review the changes:');
  console.log('   git diff');
  console.log('2. Commit the version change:');
  console.log(`   git add package.json`);
  console.log(`   git commit -m "chore: bump version to ${newVersion}"`);
  console.log('3. Push to trigger publishing:');
  console.log('   git push origin main');
  
  if (type === 'beta') {
    console.log('\n🚀 This will trigger automatic beta publishing to npm');
  } else {
    console.log('\n🚀 After pushing, create a GitHub release to publish stable version');
  }
}

function showHelp() {
  console.log(`
Version Management Script for ExosphereHost TypeScript SDK

Usage:
  node scripts/version.js <type>

Types:
  beta    Create a beta version (e.g., 0.1.0b1, 0.1.0b2)
  patch   Create a patch version (e.g., 0.1.0 → 0.1.1)
  minor   Create a minor version (e.g., 0.1.0 → 0.2.0)
  major   Create a major version (e.g., 0.1.0 → 1.0.0)

Examples:
  node scripts/version.js beta    # 0.1.0 → 0.1.0b1
  node scripts/version.js patch   # 0.1.0b1 → 0.1.0
  node scripts/version.js minor   # 0.1.0 → 0.2.0
  node scripts/version.js major   # 0.1.0 → 1.0.0

Current version: ${getCurrentVersion()}
`);
}

// Main execution
const args = process.argv.slice(2);

if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
  showHelp();
} else {
  const versionType = args[0];
  updateVersion(versionType);
}
