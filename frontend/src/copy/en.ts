/**
 * Central copy dictionary for EduTrace (English).
 *
 * Microcopy guidelines:
 * - Plain English: clear, concise, direct instructions without regulatory jargon.
 * - Sentence case: only the first word and proper nouns/acronyms are capitalized in headings and labels.
 * - Action-oriented buttons: all buttons start with an imperative verb (e.g. "Submit", "Download", "Save").
 * - Jargon explanation: terms like APAAR, approved intake, and supernumerary seats are explained on first use.
 * - Prepared for future localization (e.g. Hindi in copy/hi.ts).
 */

import {
  PRODUCT_NAME,
  TAGLINE,
  SHORT_DESCRIPTION,
  SUPPORT_EMAIL,
  GRIEVANCE_EMAIL,
  GRIEVANCE_OFFICER,
  APAAR_EXPLAINER,
  DEMO_MODE_NOTICE,
} from "../brand";

export const en = {
  brand: {
    name: PRODUCT_NAME,
    tagline: TAGLINE,
    description: SHORT_DESCRIPTION,
    supportEmail: SUPPORT_EMAIL,
    grievanceEmail: GRIEVANCE_EMAIL,
    grievanceOfficer: GRIEVANCE_OFFICER,
    apaarExplainer: APAAR_EXPLAINER,
    demoModeNotice: DEMO_MODE_NOTICE,
  },

  common: {
    actions: {
      submit: "Submit",
      save: "Save changes",
      saveDraft: "Save draft",
      cancel: "Cancel",
      close: "Close dialog",
      confirm: "Confirm",
      back: "Go back",
      next: "Continue",
      previous: "Go to previous step",
      retry: "Retry",
      refresh: "Refresh data",
      search: "Search records",
      filter: "Apply filter",
      clearFilter: "Clear filters",
      reset: "Reset to defaults",
      download: "Download file",
      downloadCsv: "Download CSV template",
      downloadReport: "Download report",
      downloadCertificate: "Download verified certificate",
      upload: "Upload file",
      browse: "Browse files",
      edit: "Edit record",
      delete: "Delete record",
      remove: "Remove item",
      add: "Add student",
      verify: "Verify record",
      view: "View details",
      viewTable: "View as table",
      viewChart: "View as chart",
      viewRecords: "View student records",
      export: "Export records",
      copy: "Copy to clipboard",
      toggle: "Toggle view",
      open: "Open details",
      sign: "Sign declaration",
      signOut: "Sign out",
      logIn: "Log in",
      check: "Check status",
    },
    status: {
      draft: "Draft",
      valid: "Valid",
      flagged: "Flagged",
      submitted: "Submitted",
      underReview: "Under review",
      accepted: "Accepted",
      rejected: "Rejected",
      approved: "Approved",
      pending: "Pending",
      active: "Active",
      suspended: "Suspended",
      expired: "Expired",
      withdrawn: "Withdrawn",
      live: "Live",
      reconnecting: "Reconnecting",
    },
    flags: {
      error: "Error",
      exception: "Exception",
      warning: "Warning",
      info: "Info",
    },
    pagination: {
      previous: "Previous page",
      next: "Next page",
      pageOf: "Page {page} of {total}",
      showingRange: "Showing {start} to {end} of {total} records",
      rowsPerPage: "Rows per page:",
    },
    table: {
      empty: "No records found",
      emptyFilter: "No records match the selected filters. Clear filters to see all rows.",
      loading: "Loading records from database...",
      error: "Failed to load records. Check connection and retry.",
    },
  },

  nav: {
    home: "Home",
    activate: "Activate college",
    collegeLogin: "College login",
    aicteLogin: "AICTE login",
    verify: "Verify student",
    studentPortal: "Student portal",
    terms: "Terms of service",
    privacy: "Privacy charter",
    accessibility: "Accessibility statement",
    help: "Help and glossary",
    skipLink: "Skip to main content",
  },

  footer: {
    prototypeNotice: DEMO_MODE_NOTICE,
    copyright: "All India Council for Technical Education (AICTE) • Ministry of Education, Govt. of India",
    systemName: `${PRODUCT_NAME} • Student data management and verification system`,
    grievanceLabel: "Grievance officer:",
    supportLabel: "Support:",
  },

  help: {
    title: "Help and glossary",
    subtitle: "Plain-language explanations of regulatory, technical, and domain concepts used in EduTrace.",
    regulatoryHeading: "Regulatory and academic terms",
    terms: [
      {
        term: "APAAR ID",
        definition:
          "Automated Permanent Academic Account Registry identifier. A 12-digit unique national academic ID issued to students in India under the One Nation, One Student ID initiative. EduTrace does not store Aadhaar numbers.",
      },
      {
        term: "Approved intake",
        definition:
          "The maximum number of regular student admissions sanctioned by AICTE for a specific course and academic year. Enrolling more regular students than this ceiling triggers an over-intake regulatory exception.",
      },
      {
        term: "Supernumerary seats",
        definition:
          "Special quota seats sanctioned by AICTE over and above the regular intake ceiling (such as Tuition Fee Waiver, PMSSS, J&K quota, NRI, OCI, and foreign nationals). Supernumerary students are counted separately from regular intake.",
      },
      {
        term: "Seat declaration",
        definition:
          "A formal declaration filed by an institution listing its total admitted students divided into regular and supernumerary categories for each course before submitting individual student records.",
      },
      {
        term: "Validation exception",
        definition:
          "A real-world compliance problem shown by the data (such as regular intake exceeded or duplicate enrolment at another college). Exceptions do not silently discard data; they require a written justification from the college and AICTE review before final approval.",
      },
      {
        term: "Duplicate enrolment",
        definition:
          "An anomaly where the same APAAR ID appears active in multiple institutions or courses during the same academic year. Cross-institution validation flags both colleges so the student can be properly transferred or withdrawn.",
      },
      {
        term: "Consent-gated verification",
        definition:
          "A privacy-preserving verification mechanism where third parties (employers or higher education institutions) cannot view a student's record without one-time cryptographic consent authorized by the student.",
      },
      {
        term: "Hash-chained audit log",
        definition:
          "An append-only security ledger where every state change, data edit, and verification read is chained to the SHA-256 hash of the previous log entry, ensuring that any tampering is immediately detected.",
      },
      {
        term: "Isolation forest anomaly detection",
        definition:
          "A machine learning algorithm that analyzes intake patterns across colleges and historical years to flag statistically unusual admission jumps, abnormal NRI quotas, or sudden demographic clusters for AICTE oversight.",
      },
      {
        term: "Digital Personal Data Protection Act (DPDP Act)",
        definition:
          "India's statutory data protection framework. EduTrace adheres to DPDP principles of purpose limitation, data minimization (no Aadhaar, parent details, or biometric storage), and active consent.",
      },
    ],
  },

  auth: {
    college: {
      title: "College portal login",
      subtitle: "Sign in with your institution administrator or staff credentials to manage student data.",
      emailLabel: "Official email address",
      emailHint: "Use the institutional email registered during account activation.",
      passwordLabel: "Password",
      mfaLabel: "Six-digit authenticator code",
      mfaHint: "Enter the time-based one-time code from your authenticator application.",
      submitButton: "Sign in to college portal",
      invalidCredentials: "The email address, password, or security credentials entered are incorrect. Try again.",
      quickFillTitle: "Quick demo credentials:",
    },
    aicte: {
      title: "AICTE oversight login",
      subtitle: "Sign in with your AICTE officer or administrator credentials for central monitoring.",
      emailLabel: "Official officer email",
      emailHint: "Use your authorized AICTE administrative email address.",
      passwordLabel: "Password",
      mfaLabel: "Six-digit security token",
      mfaHint: "Enter the administrative MFA code generated by your hardware or software authenticator.",
      submitButton: "Sign in to AICTE oversight portal",
      invalidCredentials: "The email address, password, or security credentials entered are incorrect. Try again.",
      quickFillTitle: "Quick demo credentials:",
    },
  },

  home: {
    heroTitle: "Verified student records for every AICTE college",
    heroSubtitle:
      "A unified national platform for AICTE-approved institutions to upload, validate, and monitor student admissions using the 12-digit APAAR ID.",
    howItWorksHeading: "How the verification pipeline works",
    steps: [
      {
        number: "1",
        title: "Upload student admissions",
        description:
          "Colleges submit student enrolment data using single entry, bulk CSV upload, or direct ERP API integration keyed by APAAR ID.",
      },
      {
        number: "2",
        title: "Automated compliance checks",
        description:
          "The engine validates student records against national APAAR registries, AICTE approved intake quotas, and cross-college duplicates.",
      },
      {
        number: "3",
        title: "AICTE central oversight",
        description:
          "Regulators monitor real-time enrolment dashboards, review justified compliance exceptions, and detect statistical anomalies.",
      },
      {
        number: "4",
        title: "Student consent verification",
        description:
          "Students control access to their records via one-time consent, allowing employers and agencies to verify credentials securely.",
      },
    ],
    cardsHeading: "Choose your portal to begin",
    cards: {
      activate: {
        title: "Activate college",
        description: "Claim your AICTE institution master entry, verify official contacts with OTP, and set up your admin account.",
        button: "Activate your college",
      },
      college: {
        title: "College login",
        description: "Upload student batches, manage seat quotas, review validation flags, and file formal compliance justifications.",
        button: "Log in as college",
      },
      aicte: {
        title: "AICTE login",
        description: "Review institutional submissions, monitor intake ceilings, manage approved courses, and track anomalies.",
        button: "Log in as AICTE",
      },
      verify: {
        title: "Verify student",
        description: "Look up verified student credentials with student consent, or scan signed cryptographic QR codes.",
        button: "Verify a student record",
      },
      student: {
        title: "Student portal",
        description: "Review colleges that hold your enrolment records and manage third-party verification consent requests.",
        button: "Open student portal",
      },
    },
  },

  activate: {
    title: "Activate your institution account",
    subtitle: "Claim an existing AICTE master list entry and initialize the primary administrator account.",
    step1Title: "Step 1: Enter AICTE permanent institute identifier",
    step1Subtitle: "Enter the official permanent institution ID assigned to your college by AICTE.",
    step2Title: "Step 2: Enter verification code",
    step2Subtitle: "A 6-digit verification code has been dispatched to the official contacts on file.",
    step3Title: "Step 3: Authorized signatory verification and letter",
    step3Subtitle: "Verify the head of the institution and provide the official authorization letter.",
    step4Title: "Activation claim successfully submitted",
    step4Subtitle: "Your activation request has been forwarded to the AICTE review queue for statutory approval.",
    checkStatusTitle: "Institution claim status lookup",
    actions: {
      startWizard: "Start activation wizard",
      checkStatus: "Check claim status",
      verifyInstitution: "Verify institution ID",
      sendOtp: "Send OTP to official contact",
      changeId: "Change institution ID",
      verifyOtp: "Verify OTP code",
      uploadLetter: "Upload authorization letter",
      submitClaim: "Submit activation claim",
      trackClaim: "Track claim status",
      returnHome: "Return to home",
      goToLogin: "Go to college login",
    },
  },

  college: {
    dashboard: {
      title: "College admission dashboard",
      subtitle: "Overview of approved course intake, admitted student totals, and compliance status for the active academic year.",
      coursesHeading: "Approved courses and intake summary",
      pendingFlagsHeading: "Pending validation flags",
      recentSubmissionsHeading: "Submission history and receipts",
      queriesHeading: "AICTE clarification inquiries",
      notificationsHeading: "Regulatory notifications",
      actions: {
        uploadCsv: "Upload student CSV",
        addStudent: "Add single student",
        declareSeats: "Update seat declarations",
        reviewFlags: "Review validation flags",
        proceedToSubmit: "Proceed to submission gate",
      },
    },
    seats: {
      title: "Seat declarations and course quotas",
      subtitle: "Declare institutional regular and supernumerary admissions for each approved course before final submit.",
      summaryHeading: "Declared seats summary",
      coursesHeading: "Course intake declarations",
      aicteControlledNote: "Set by AICTE: approved intake ceiling and allowed supernumerary quotas are read-only.",
      requestCorrection: "Request intake correction",
      saveDeclarations: "Save seat declarations",
    },
    students: {
      title: "Enrolled students directory",
      subtitle: "Manage, filter, and inspect student admission records registered under your institution.",
      addStudentButton: "Add single student",
      uploadCsvButton: "Upload student CSV",
      filterByCourse: "Filter by course",
      filterByStatus: "Filter by status",
      filterByCategory: "Filter by category",
      searchPlaceholder: "Search by student name, APAAR ID, or enrolment number...",
      deleteConfirm: "Are you sure you want to delete this draft student record? This action cannot be undone.",
    },
    studentForm: {
      addTitle: "Add new student record",
      editTitle: "Edit student admission record",
      subtitle: "Enter verified student details keyed by the 12-digit national APAAR ID.",
      group1Title: "1. Identity details",
      group1Subtitle: "Academic identity attributes verified against the national APAAR registry.",
      group2Title: "2. Admission details",
      group2Subtitle: "Institutional programme, enrolment identifier, and admission mode.",
      group3Title: "3. Category and nationality",
      group3Subtitle: "Social reservation category and foreign national quota classifications.",
      liveValidationHeading: "Live validation findings",
      actions: {
        saveStudent: "Save student record",
        cancel: "Cancel and return to list",
      },
    },
    upload: {
      title: "Bulk student data upload",
      subtitle: "Upload institution admission records in bulk using standard CSV format.",
      dropzoneTitle: "Drag and drop student CSV file here",
      dropzoneSubtitle: "File must follow the official lower-case header schema. Maximum 10,000 rows.",
      browseFiles: "Browse files",
      downloadTemplate: "Download CSV template",
      resultsHeading: "Upload validation results",
      passedRows: "Passed clean",
      flaggedRows: "Flagged with findings",
      actions: {
        startUpload: "Upload student data",
        downloadErrors: "Download flagged error rows",
        reviewFindings: "Review validation findings",
        reupload: "Upload updated CSV",
      },
    },
    validation: {
      title: "Validation findings and exceptions",
      subtitle: "Inspect open validation flags, review error causes, and submit justifications for compliance exceptions.",
      tabs: {
        all: "All flags",
        errors: "Errors (blocks submit)",
        exceptions: "Exceptions (requires justification)",
        warnings: "Warnings",
        info: "Informational",
      },
      emptyFlags: "No validation flags detected. All student records satisfy regulatory validation rules.",
      submitJustification: "Submit written justification",
    },
    submit: {
      title: "Annual student data submission",
      subtitle: "Verify institutional compliance checklist, confirm declarations, and lock admission records.",
      gateChecklistHeading: "Submission gate checklist",
      declarationHeading: "Statutory institutional declaration",
      declarationText: "I hereby confirm on behalf of the institution that all admitted student records, seat quotas, and reservation categories uploaded for this academic year are accurate and truthful.",
      otpHeading: "Administrator OTP authorization",
      actions: {
        requestOtp: "Request declaration OTP",
        verifyAndSubmit: "Submit and lock institutional records",
        downloadReceipt: "Download formal submission receipt",
      },
    },
    queries: {
      title: "AICTE clarification inquiries",
      subtitle: "Review and respond to clarification requests raised by AICTE reviewers during submission review.",
      respondButton: "Respond to inquiry",
      submitResponse: "Submit response to AICTE",
    },
    changeRequests: {
      title: "Post-lock change requests",
      subtitle: "Submit formal correction requests for student records locked following final submission.",
      newRequestButton: "File new change request",
      submitRequest: "Submit change request to AICTE",
    },
    staff: {
      title: "Institutional staff management",
      subtitle: "Manage staff accounts and assign admission officer or viewer permissions.",
      createStaffButton: "Create staff account",
    },
    apiKeys: {
      title: "Integration API credentials",
      subtitle: "Generate and rotate scoped API keys for automated student data synchronization from institutional ERP systems.",
      generateKeyButton: "Generate integration API key",
      revokeKeyButton: "Revoke API key",
    },
  },

  aicte: {
    overview: {
      title: "Central oversight and analytics dashboard",
      subtitle: "Real-time national monitoring of student enrolments, approved intake quotas, and compliance exceptions across AICTE-approved institutions.",
      kpis: {
        totalColleges: "Approved institutions",
        totalStudents: "Enrolled students",
        submissionRate: "Submissions completed",
        openExceptions: "Open exceptions",
      },
      charts: {
        stateIntake: "Intake and enrolment by state",
        submissionProgress: "Institutional submission progress",
        courseDistribution: "Approved quotas and enrolment by course",
      },
      redListHeading: "Over-intake compliance red list",
      liveStreamHeading: "Live system activity stream",
      modulesHeading: "AICTE regulatory oversight modules",
    },
    approvals: {
      title: "Institution approvals queue",
      subtitle: "Review activation requests from AICTE-approved colleges claiming their institutional accounts.",
      approveButton: "Approve activation claim",
      rejectButton: "Reject activation claim",
    },
    intake: {
      title: "AICTE intake and approval control",
      subtitle: "Manage statutory intake ceilings, course authorizations, and institution approval statuses.",
      updateIntakeButton: "Update approved intake",
      updateStatusButton: "Update approval status",
    },
    compliance: {
      title: "Over-intake compliance and red list",
      subtitle: "Monitor colleges where regular student admissions exceed AICTE approved intake quotas.",
      exportListButton: "Export compliance red list",
    },
    duplicates: {
      title: "Cross-institution duplicate enrolments",
      subtitle: "Detect and resolve instances where one student is enrolled at multiple colleges during the same academic year.",
      markResolvedButton: "Mark duplicate resolved",
    },
    anomalies: {
      title: "Intelligent anomaly detection and pattern recognition",
      subtitle: "Machine learning Isolation Forest and statistical flags highlighting unusual admission jumps and demographic patterns.",
      runAnalysisButton: "Run anomaly detection",
    },
    review: {
      title: "AICTE submission review queue",
      subtitle: "Inspect institutional submissions with compliance exceptions, examine written justifications, and record regulatory decisions.",
      acceptButton: "Accept submission",
      queryButton: "Raise clarification query",
      escalateButton: "Escalate to committee",
    },
    drilldown: {
      title: "Institutional data explorer and student auditing",
      subtitle: "Drill down through national statistics, state totals, institutions, approved courses, and individual student records.",
      breadcrumbs: {
        national: "All states (national)",
        state: "State",
        college: "Institution",
        course: "Course",
        students: "Flagged students",
      },
    },
    reports: {
      title: "Regulatory and compliance reports",
      subtitle: "Generate and download statutory reports in CSV, Excel, and PDF formats for accreditation and policy planning.",
      generateButton: "Generate report",
    },
    audit: {
      title: "Cryptographic audit trail and tamper verification",
      subtitle: "Inspect the append-only SHA-256 hash-chained audit log recording all administrative state changes and data access events.",
      verifyChainButton: "Verify cryptographic hash chain",
    },
    verifiers: {
      title: "Third-party verifier management",
      subtitle: "Review registration applications and manage permissions for third-party verification organizations.",
      approveOrgButton: "Approve verifier organization",
      revokeOrgButton: "Revoke verifier access",
    },
    rules: {
      title: "Validation rules and policy customization",
      subtitle: "Configure severity levels, parameters, and enforcement toggles for all validation engine rules without code changes.",
      savePolicyButton: "Save policy configuration",
    },
  },

  verifier: {
    search: {
      title: "Student credential verification",
      subtitle: "Verify academic records of candidates by requesting cryptographic consent via their 12-digit APAAR ID.",
      apaarInputLabel: "Candidate APAAR ID",
      apaarInputHint: "Enter the candidate's 12-digit academic ID. A consent request will be dispatched to their registered phone and email.",
      requestConsentButton: "Request candidate consent",
      verifiedHeading: "Verified academic record",
      verifiedSubtitle: "Official enrolment credentials attested by AICTE central repository.",
    },
    history: {
      title: "Verification and consent history",
      subtitle: "Audit log of all student consent requests initiated by your organization.",
      newSearchButton: "Start new verification",
    },
  },

  student: {
    portal: {
      title: "Student academic identity and consent portal",
      subtitle: "Manage your academic identity, review institutions holding your records, and grant or deny verification requests.",
      loginHeading: "Student access sign-in",
      apaarLabel: "12-digit APAAR ID",
      otpLabel: "One-time verification code",
      verifyOtpButton: "Verify and access records",
      recordsHeading: "Institutions holding your academic record",
      consentHeading: "Pending third-party verification requests",
      approveConsentButton: "Approve verification request",
      denyConsentButton: "Deny verification request",
      accessLogHeading: "Access and verification history",
      downloadCertificate: "Download degree certificate PDF",
    },
  },
} as const;

export default en;
