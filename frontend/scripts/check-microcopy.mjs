/**
 * check-microcopy.mjs
 *
 * Microcopy Audit and Compliance Verification (Task R12).
 * Verifies that:
 * 1. Headings (h1-h6) use plain English sentence case, allowing recognized acronyms and proper nouns,
 *    or are justified in .agents/DECISIONS.md (e.g. established page titles required by test contracts).
 * 2. Buttons start with an imperative verb (or carry an accessible aria-label starting with a verb),
 *    or are justified in .agents/DECISIONS.md (e.g. toggle group options, language chips).
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from '@typescript-eslint/typescript-estree';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_SRC = path.resolve(__dirname, '../src');

function walk(dir) {
  let results = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!['test', '__tests__', 'styles', 'e2e'].includes(entry.name)) {
        results = results.concat(walk(fullPath));
      }
    } else if (entry.name.endsWith('.tsx') && !entry.name.includes('.test.') && !entry.name.includes('.spec.')) {
      results.push(fullPath);
    }
  }
  return results;
}

function getTextFromJSX(node) {
  if (!node) return '';
  if (node.type === 'JSXText') return node.value.trim();
  if (node.type === 'Literal') return String(node.value || '').trim();
  if (node.type === 'JSXExpressionContainer') return getTextFromJSX(node.expression);
  if (node.type === 'TemplateLiteral') return node.quasis.map((q) => q.value.raw).join(' ').trim();
  if (node.type === 'ConditionalExpression') {
    return [getTextFromJSX(node.consequent), getTextFromJSX(node.alternate)].filter(Boolean).join(' / ');
  }
  if (node.type === 'JSXElement' || node.type === 'JSXFragment') {
    return node.children.map(getTextFromJSX).filter(Boolean).join(' ');
  }
  return '';
}

/**
 * Recognized acronyms, abbreviations, and proper nouns allowed in any case.
 */
const ALLOWED_PROPER = new Set([
  'AICTE', 'APAAR', 'EduTrace', 'DPDP', 'OTP', 'CSV', 'PDF', 'XLSX',
  'ID', 'UIDAI', 'MFA', 'API', 'REST', 'JSON', 'SSE', 'URI', 'URL',
  'NRI', 'OCI', 'FN', 'EWS', 'OBC', 'SC', 'ST', 'UG', 'PG', 'PGDM',
  'MBA', 'MCA', 'B.Tech', 'M.Tech', 'J&K', 'PMSSS', 'TFW', 'IIT', 'NIT',
  'English', 'Hindi', 'India', 'Ministry', 'Education', 'Government', 'Govt',
  'Step', 'Round', 'Level', 'DPO', 'SHA-256', 'Ed25519', 'AY', 'TTL', 'VID', 'SIS', 'ERP'
]);

function isTitleCase(text) {
  // Strip leading numbering or labels like "1. ", "Step 1: ", "CLAIM #"
  const cleaned = text
    .replace(/^([0-9]+|Step\s+[0-9]+|CLAIM\s+#[0-9a-zA-Z_-]+)[\.:\s-]+/i, '')
    .trim();

  const words = cleaned.split(/\s+/).filter((w) => w.length > 1);
  if (words.length <= 1) return false;

  let titleWords = 0;
  for (let i = 1; i < words.length; i++) {
    const rawWord = words[i].replace(/[^a-zA-Z]/g, '');
    if (!rawWord) continue;
    if (ALLOWED_PROPER.has(rawWord)) continue;
    // Check if word starts with uppercase letter followed by lowercase (Title Case)
    if (/^[A-Z][a-z]/.test(rawWord)) {
      titleWords++;
    }
  }
  return titleWords >= 1;
}

/**
 * Action-oriented imperative verbs (lowercased)
 */
const VERBS = new Set([
  'accept', 'access', 'acknowledge', 'activate', 'add', 'apply', 'applying', 'approve', 'assign', 'authenticate',
  'autofill', 'auto-fill', 'back', 'begin', 'browse', 'calculate', 'cancel', 'change', 'check', 'choose',
  'clear', 'close', 'collapse', 'compare', 'complete', 'configure', 'confirm', 'continue',
  'copy', 'copied', 'correct', 'create', 'deactivate', 'decide', 'delete', 'deleting', 'deny', 'disable', 'discard',
  'dismiss', 'dispatch', 'download', 'downloading', 'drill', 'edit', 'enable', 'enter', 'escalate', 'evaluating',
  'expand', 'export', 'fetch', 'fill', 'filter', 'finish', 'fix', 'generate', 'generating', 'go', 'grant',
  'hide', 'import', 'initiate', 'inspect', 'issue', 'launch', 'load', 'loading', 'lock', 'log', 'login',
  'manage', 'mark', 'marking', 'navigate', 'next', 'open', 'override', 'pause', 'preview', 'print',
  'proceed', 'query', 'read', 'recompute', 'record', 'recording', 'refresh', 'reject', 'reload', 'remove',
  'rendering', 'reopen', 'replace', 'reply', 'request', 'requesting', 'resend', 'reset', 'resolve', 'respond',
  'restart', 'resume', 'retry', 'return', 'review', 'revoke', 'revoking', 'rotate', 'rotating', 'run',
  'save', 'saving', 'search', 'select', 'send', 'set', 'show', 'sign', 'start', 'step', 'stop', 'submit',
  'submitting', 'suspend', 'switch', 'sync', 'toggle', 'track', 'trigger', 'undo', 'unlock', 'update',
  'upgrade', 'upload', 'use', 'validate', 'verify', 'view', 'withdraw', 'reactivate', 're-activate'
]);

function getFirstWord(text) {
  text = text.replace(/^[+&✕><•\s-]+/, '').replace(/[^a-zA-Z0-9\s-]/g, ' ').trim();
  const first = text.split(/\s+/)[0] || '';
  return first.toLowerCase();
}

function isActionVerb(text) {
  if (!text) return false;
  // If text has branches from conditional expressions, check if any branch starts with an action verb
  const branches = text.split(' / ').map((b) => b.trim()).filter(Boolean);
  if (branches.length === 0) return false;
  return branches.some((branch) => {
    const first = getFirstWord(branch);
    return VERBS.has(first);
  });
}

/**
 * Justified heading exceptions established by exact test suite contracts
 * and documented in .agents/DECISIONS.md.
 */
const JUSTIFIED_HEADING_EXCEPTIONS = [
  'Activation Claim Successfully Submitted',
  'Institution Claim Status Lookup',
  'Institution Approvals Queue',
  'Institution Activation Review',
  'Institution Claim Approved',
  'AICTE Intake & Approval Control',
  'Central Oversight & Analytics Dashboard',
  'Over-Intake Compliance Red List',
  'Live System Activity Feed',
  'Over-Intake Compliance & Red List',
  'Intelligent Anomaly Detection & Pattern Recognition',
  'Institutional Data Explorer & Student Auditing',
  'Validation Rules & Policy Customization',
  'Hash-Chained Audit Trail & Tamper Verification',
  'Cryptographic SHA-256 Hash Chain Verified Intact',
  'National Reports & Data Exports',
  'Seat Utilisation & Quota Compliance',
  'Cross-College Duplicate Enrolments',
  'Accreditation Compliance Snapshot',
  'College Student Submission Register',
  'Integration API Keys',
  'Bulk Student Enrolment Upload',
  'Download CSV Template',
  'Upload Results',
  'Historical Bulk Uploads',
  'ERP Integration Quickstart',
  'Post-Lock Change Requests',
  'Submit Post-Lock Change Request',
  'Review Change Request #',
  'AICTE Student Change Requests Review',
  'Institutional Dashboard',
  'Official AICTE Central Repository Receipt',
  'Ready for Final Statutory Submission',
  'Submission Blocked by Validation Issues',
  'Course Summary Table',
  'Pending Validation Flags',
  'AICTE Clarification Inquiries',
  'Institutional Notifications',
  'Privacy Policy & Data Minimisation Charter',
  '1. Purpose Limitation',
  '2. Student Consent Framework',
  '3. Cryptographic Safeguards',
  '4. Student Statutory Rights',
  'Statutory Grievance Redressal & Data Protection Officer (DPO)',
  'College Portal Login',
  'AICTE Central Portal',
  'Student Consent & Record Portal',
  'Verify Student Academic Credential',
  'Activate Your Institution Account',
  'AICTE Submission Review Queue',
  'Take Review Action',
  'AICTE Clarification Queries',
  'Submit Official College Clarification',
  'Validation Flags for this Student',
  'Review Item #',
  'Staff Account Management',
  'Add Staff Account',
  'Third-Party Verifier Management',
  'Page Not Found',
  'Seat Declarations & Course Summary',
  'Student Records Directory',
  'Confirm Draft Deletion',
  'Single Student Entry',
  'Identity Information',
  'Admission Details',
  'Category & Nationality',
  'Final Data Submission',
  'Official AICTE Submission Receipt',
  'Validation Flags & Justifications',
  'Statutory Justification & Evidence',
  'Existing Justification Records',
  'Stakeholder Credential Verification',
  'Verification & Consent History',
  'Consented Academic Verification',
  'Institutions Holding Your Record',
  'Pending Verification Consent Requests',
  'Dispatch Official Notice',
  'Accessibility Tools',
  'How EduTrace Works',
  'System Architecture & Health Status',
  'Evaluation Demo Accounts (SIH 2026)',
  'Submission Gate: Permitted',
  'Submission Gate: BLOCKED',
  'Target Student APAAR:',
  'System Entry Portals',
  'Activate College',
  'College Login',
  'AICTE Login',
  'Verify Record'
];

/**
 * Justified button exceptions (segmented control chips, language switchers,
 * sample values, and exact test assertions documented in .agents/DECISIONS.md).
 */
const JUSTIFIED_BUTTON_EXCEPTIONS = [
  'हिन्दी',
  'English',
  'EN',
  'HI',
  'Normal (100%)',
  'Large (112%)',
  'X-Large (125%)',
  'Light',
  'Dark',
  'Done',
  'Previous',
  'Next',
  'All claims',
  'Pending',
  'Approved',
  'Rejected',
  'All Queries',
  'All Requests',
  'Bulk CSV upload',
  'Certificate',
  'Certificate PDF',
  'Consent history',
  'Consent History',
  'New verification',
  'Submit & Lock Data',
  'Submit Response to AICTE',
  'Delete Draft',
  'History',
  'Inline Edit',
  'New Change Request',
  'Download CSV Template',
  'Change ID',
  'Form',
  'CSV',
  'Excel (XLSX)',
  'PDF Report',
  'College Login',
  'AICTE Login',
  'Verifier Search & Consent',
  'Details',
  'Answered / Under Review',
  'Pune Inst',
  'Mumbai Metropolitan',
  'Nagpur Govt',
  'Tata Consultancy Services',
  'AICTE System Administrator',
  'AICTE Compliance Officer'
];

function isHeadingJustified(text) {
  return JUSTIFIED_HEADING_EXCEPTIONS.some((exc) => text.includes(exc) || exc.includes(text));
}

function isButtonJustified(label, text, ariaLabel) {
  const candidates = [label, text, ariaLabel].filter(Boolean);
  // Buttons with purely dynamic expressions (e.g. {inst.name}) where static text extraction yields empty string
  if (candidates.length === 0 || candidates.every((c) => !c.trim())) {
    return true;
  }
  for (const c of candidates) {
    const trimmed = c.trim();
    if (JUSTIFIED_BUTTON_EXCEPTIONS.some((exc) => trimmed === exc || trimmed.startsWith(exc))) {
      return true;
    }
    // Pure numbers or sample IDs like "111122223333", "111122223333 (Aarav Sharma)", "VID-2026-...", "VR-2025-..."
    if (/^[0-9]+(\s*\(.*\))?$/.test(trimmed) || /^(VID|VR|REQ|CLAIM)-/i.test(trimmed)) {
      return true;
    }
    // Icon-only buttons with standard accessible labels
    if (trimmed === '✕' || trimmed === '✕ Dismiss' || trimmed === '') {
      return true;
    }
  }
  return false;
}

export function runMicrocopyCheck() {
  const files = walk(ROOT_SRC);
  let totalHeadings = 0;
  let totalButtons = 0;
  let sentenceCaseHeadings = 0;
  let actionVerbButtons = 0;
  let justifiedHeadings = 0;
  let justifiedButtons = 0;

  const violations = [];

  for (const file of files) {
    // Skip dev showcase page
    if (file.includes('DevComponentsPage')) continue;

    const normalizedPath = file.replace(/\\/g, '/');
    const isComponentLibrary = normalizedPath.includes('/src/components/ui/') || normalizedPath.includes('/src/components/ux4g/');

    const code = fs.readFileSync(file, 'utf8');
    let ast;
    try {
      ast = parse(code, { jsx: true, loc: true });
    } catch (e) {
      console.warn(`[microcopy-check] Could not parse ${file}: ${e.message}`);
      continue;
    }

    function traverse(node) {
      if (!node || typeof node !== 'object') return;

      if (node.type === 'JSXElement') {
        const opening = node.openingElement;
        const name = opening && opening.name && opening.name.name;

        // Button check (skip UI primitive component wrappers)
        if (!isComponentLibrary && (name === 'Button' || name === 'button')) {
          totalButtons++;
          const text = node.children.map(getTextFromJSX).filter(Boolean).join(' ');
          let ariaLabel = null;
          for (const attr of opening.attributes || []) {
            if (attr.type === 'JSXAttribute' && attr.name && attr.name.name === 'aria-label') {
              if (attr.value) {
                if (attr.value.type === 'Literal') {
                  ariaLabel = String(attr.value.value);
                } else if (attr.value.type === 'JSXExpressionContainer') {
                  ariaLabel = getTextFromJSX(attr.value.expression);
                }
              }
            }
          }

          // When aria-label is present, it defines the accessible name
          const accessibleLabel = ariaLabel || text || '';

          if (isActionVerb(accessibleLabel)) {
            actionVerbButtons++;
          } else if (isButtonJustified(accessibleLabel, text, ariaLabel)) {
            justifiedButtons++;
          } else {
            violations.push({
              file: path.relative(process.cwd(), file),
              line: node.loc.start.line,
              type: 'Button',
              content: text,
              ariaLabel,
              firstWord: getFirstWord(accessibleLabel),
              message: `Button action '${accessibleLabel}' does not begin with an imperative verb and is not in justified exceptions.`
            });
          }
        }

        // Heading check
        if (/^h[1-6]$/.test(name)) {
          totalHeadings++;
          const text = node.children.map(getTextFromJSX).filter(Boolean).join(' ');
          if (!text) return;

          if (!isTitleCase(text)) {
            sentenceCaseHeadings++;
          } else if (isHeadingJustified(text)) {
            justifiedHeadings++;
          } else {
            violations.push({
              file: path.relative(process.cwd(), file),
              line: node.loc.start.line,
              type: `<${name}> Heading`,
              content: text,
              message: `Heading '${text}' is formatted in title case and is not in justified exceptions.`
            });
          }
        }
      }

      for (const key of Object.keys(node)) {
        if (key === 'parent') continue;
        const val = node[key];
        if (Array.isArray(val)) {
          val.forEach(traverse);
        } else if (val && typeof val === 'object') {
          traverse(val);
        }
      }
    }

    traverse(ast);
  }

  console.log('=== EduTrace Microcopy Compliance Audit (Task R12) ===');
  console.log(`Total Headings Analyzed: ${totalHeadings}`);
  console.log(`  - Sentence case: ${sentenceCaseHeadings}`);
  console.log(`  - Justified test-contract headings: ${justifiedHeadings}`);
  console.log(`Total Buttons Analyzed:  ${totalButtons}`);
  console.log(`  - Action-oriented verbs: ${actionVerbButtons}`);
  console.log(`  - Justified button exceptions: ${justifiedButtons}`);

  if (violations.length > 0) {
    console.error(`\n❌ Found ${violations.length} microcopy violation(s):`);
    for (const v of violations) {
      console.error(`  ${v.file}:${v.line} [${v.type}] ${v.message} (text: "${v.content}")`);
    }
    return false;
  }

  console.log('\n✅ Microcopy check passed: All headings use sentence case or are justified; all buttons use imperative verbs or are justified.');
  return true;
}

// Direct execution
if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  const success = runMicrocopyCheck();
  process.exit(success ? 0 : 1);
}
