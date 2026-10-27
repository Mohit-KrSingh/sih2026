# APAAR Validation Rules Catalogue

> Automated generation from rule registry and contract specifications.
> Source of truth: `SPEC.md` Section 9.3 & 9.4.

## 1. Overview and Architecture

The APAAR Student Data Validation Engine provides unified, automated validation
across all channels (single student entry, CSV bulk upload, and automated API).

### 1.1 Validation Scopes & Execution Order

Per **SPEC.md Section 9.4**, rules execute following cheap-checks-first order:
1. **File Scope (`file`)**: Template validity, header checks, file size, empty rows, within-file duplicate APAAR and enrolment numbers.
2. **Row Scope (`row`)**: Format checks, mandatory field presence, registry identity lookups (batched), and internal row consistency.
3. **Course Scope (`course`)**: Approved intake quotas, supernumerary allowances, and college-declared seat counts.
4. **Cross-College Scope (`cross`)**: Cross-institution concurrent active enrolments and identical course duplicate checks.
5. **Anomaly Scope (`anomaly`)**: Statistical indicators, NRI/supernumerary spikes, date-of-birth clusters, sequential runs, and IsolationForest ML scoring.

### 1.2 Validation Levels & Submission Gate

| Level | Meaning | Submission Gate Effect | Badge Presentation |
|---|---|---|---|
| `error` | Data is wrong (typing or format mistake) | **Blocks submission** until corrected | Red filled badge |
| `exception` | Real-world compliance problem (e.g. over-intake) | **Permitted with written justification**; routed to AICTE review queue | Red outlined (2px) badge |
| `warning` | Suspicious but possibly legitimate | Permitted (justification if required) | Amber filled badge |
| `info` | Noteworthy observation | Informational only (no block, no justification) | Grey filled badge |

### 1.3 Rule Catalogue Statistics

- **Total Rules Defined:** 34
- **Registered Active Rule Handlers:** 34
- **Rules by Scope:** `anomaly`: 7, `course`: 3, `cross`: 2, `file`: 5, `row`: 17
- **Rules by Default Level:** `error`: 18, `exception`: 3, `info`: 1, `warning`: 12

---

## 2. Summary Catalogue

| Rule Code | Scope | Default Level | Requires Justification | Meaning | Default Parameters |
|---|---|---|---|---|---|
| `DUP_APAAR_IN_FILE` | `file` | `error` | No | Same APAAR ID appears twice in the upload or the college's records for that year | `None` |
| `DUP_ENROLNO_IN_COURSE` | `file` | `error` | No | Same enrolment number twice in one course and year | `None` |
| `FILE_EMPTY` | `file` | `error` | No | No data rows. File rejected | `None` |
| `FILE_TEMPLATE` | `file` | `error` | No | Wrong or missing columns. File rejected, nothing saved | `{"expected_columns": ["apaar_id", "name", "dob", "gender", "course", "branch", "admission_year", "enrolment_no", "admission_date", "admission_mode", "seat_type", "reservation_category", "nri", "oci", "foreign_national", "country"]}` |
| `FILE_TOO_LARGE` | `file` | `error` | No | Over the row limit (default 10,000). File rejected | `{"max_rows": 10000}` |
| `ADMISSION_DATE_WINDOW` | `row` | `warning` | No | Admission date outside the admission window for that year | `{"start_month": 5, "start_day": 1, "end_month": 11, "end_day": 30}` |
| `ADMISSION_YEAR_MISMATCH` | `row` | `warning` | No | Admission date does not fall in the stated academic year | `{"start_month": 4, "start_day": 1, "end_month": 6, "end_day": 30}` |
| `AGE_OUT_OF_RANGE` | `row` | `warning` | No | Age outside the course-level band (defaults: UG 15-30, PG 19-45, Diploma 14-30, PGDM 19-45) | `{"bands": {"UG": [15, 30], "PG": [19, 45], "Diploma": [14, 30], "PGDM": [19, 45]}}` |
| `APAAR_DOB_MISMATCH` | `row` | `error` | No | Date of birth differs from the registry | `None` |
| `APAAR_FORMAT` | `row` | `error` | No | Not exactly 12 digits | `None` |
| `APAAR_NAME_MISMATCH` | `row` | `warning` | No | Fuzzy name match below threshold (default 85) | `{"threshold": 85}` |
| `APAAR_NOT_FOUND` | `row` | `error` | No | ID does not exist in the registry | `None` |
| `APAAR_REQUIRED` | `row` | `error` | No | APAAR ID missing | `None` |
| `CATEGORY_CONFLICT` | `row` | `error` | No | NRI and foreign national both Yes | `None` |
| `COUNTRY_REQUIRED` | `row` | `error` | No | Foreign national is Yes but country is empty | `None` |
| `COURSE_NOT_APPROVED` | `row` | `error` | No | Course or branch not approved for this college | `None` |
| `DOB_INVALID` | `row` | `error` | No | Not a valid date, or in the future | `None` |
| `ENUM_INVALID` | `row` | `error` | No | Value not in the allowed list (gender, category, seat type, mode, Yes/No) | `{"allowed_enums": {"gender": ["Female", "Male", "Other"], "reservation_category": ["EWS", "General", "OBC", "SC", "ST"], "seat_type": ["Regular", "Supernumerary"], "admission_mode": ["Direct second year", "JEE Main counselling", "Management quota", "NRI/OCI/foreign quota", "Other", "State counselling"], "nri": ["No", "Yes"], "oci": ["No", "Yes"], "foreign_national": ["No", "Yes"]}}` |
| `MODE_CATEGORY_MISMATCH` | `row` | `warning` | No | NRI/OCI/foreign student not admitted through the NRI/OCI/foreign quota, or the reverse | `None` |
| `NAME_FORMAT` | `row` | `error` | No | Name has digits or illegal characters | `None` |
| `NAME_REQUIRED` | `row` | `error` | No | Name missing | `None` |
| `SEAT_TYPE_NOT_APPROVED` | `row` | `error` | No | Supernumerary seat in a course with no supernumerary seats allowed | `None` |
| `INTAKE_EXCEEDED` | `course` | `exception` | Yes | Regular admitted is above approved intake. Message states the exact overshoot | `None` |
| `SEAT_DECLARATION_MISMATCH` | `course` | `error` | No | Declared counts differ from uploaded student list. Blocks submit; college fixes either | `None` |
| `SUPERNUMERARY_EXCEEDED` | `course` | `exception` | Yes | Supernumerary admitted is above the supernumerary seats AICTE allows | `None` |
| `DUP_ACTIVE_OTHER_COLLEGE` | `cross` | `warning` | No | APAAR ID is active at another AICTE college this academic year. Both colleges notified. Resolved when one marks student withdrawn or transferred | `{"exclude_same_course": false}` |
| `DUP_SAME_COURSE_OTHER_COLLEGE` | `cross` | `exception` | Yes | Same APAAR ID in the same course and year at another college | `None` |
| `ANOM_DOB_CLUSTER` | `anomaly` | `warning` | No | Many students share one date of birth (default 5 or more). Audience: aicte | `{"threshold_count": 5}` |
| `ANOM_ENROLMENT_JUMP` | `anomaly` | `warning` | No | Enrolment up more than a threshold (default 30%) against last year. Audience: aicte | `{"threshold_percent": 30.0}` |
| `ANOM_MODEL_SCORE` | `anomaly` | `warning` | No | IsolationForest score on college-course features flags this as unusual. Audience: aicte | `{"threshold_score": -0.05, "contamination": 0.08}` |
| `ANOM_NRI_SHARE` | `anomaly` | `warning` | No | NRI/OCI/foreign share unusually high (default over 25%). Audience: aicte | `{"threshold_percent": 25.0}` |
| `ANOM_SAME_ADMISSION_DAY` | `anomaly` | `info` | No | Large share of students admitted on one day (default over 60%). Audience: aicte | `{"threshold_percent": 60.0, "min_students": 5}` |
| `ANOM_SEQUENTIAL_APAAR` | `anomaly` | `warning` | No | Long runs of sequential APAAR IDs (default 10 or more). Audience: aicte | `{"threshold_run": 10}` |
| `ANOM_SUPERNUM_SHARE` | `anomaly` | `warning` | No | Supernumerary share unusually high (default over 15%). Audience: aicte | `{"threshold_percent": 15.0}` |

---

## 3. Detailed Rule Specifications by Scope

### 3.1 File-Level Rules & Upload Integrity

#### `DUP_APAAR_IN_FILE`

- **Meaning:** Same APAAR ID appears twice in the upload or the college's records for that year
- **Scope:** `file`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** No

#### `DUP_ENROLNO_IN_COURSE`

- **Meaning:** Same enrolment number twice in one course and year
- **Scope:** `file`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** No

#### `FILE_EMPTY`

- **Meaning:** No data rows. File rejected
- **Scope:** `file`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** No

#### `FILE_TEMPLATE`

- **Meaning:** Wrong or missing columns. File rejected, nothing saved
- **Scope:** `file`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `{"expected_columns": ["apaar_id", "name", "dob", "gender", "course", "branch", "admission_year", "enrolment_no", "admission_date", "admission_mode", "seat_type", "reservation_category", "nri", "oci", "foreign_national", "country"]}`
- **Requires Justification on Exception:** No

#### `FILE_TOO_LARGE`

- **Meaning:** Over the row limit (default 10,000). File rejected
- **Scope:** `file`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `{"max_rows": 10000}`
- **Requires Justification on Exception:** No

### 3.2 Row-Level Format, Field & Identity Rules

#### `ADMISSION_DATE_WINDOW`

- **Meaning:** Admission date outside the admission window for that year
- **Scope:** `row`
- **Default Level:** `warning`
- **Implementation Status:** Active
- **Default Parameters:** `{"start_month": 5, "start_day": 1, "end_month": 11, "end_day": 30}`
- **Requires Justification on Exception:** No

#### `ADMISSION_YEAR_MISMATCH`

- **Meaning:** Admission date does not fall in the stated academic year
- **Scope:** `row`
- **Default Level:** `warning`
- **Implementation Status:** Active
- **Default Parameters:** `{"start_month": 4, "start_day": 1, "end_month": 6, "end_day": 30}`
- **Requires Justification on Exception:** No

#### `AGE_OUT_OF_RANGE`

- **Meaning:** Age outside the course-level band (defaults: UG 15-30, PG 19-45, Diploma 14-30, PGDM 19-45)
- **Scope:** `row`
- **Default Level:** `warning`
- **Implementation Status:** Active
- **Default Parameters:** `{"bands": {"UG": [15, 30], "PG": [19, 45], "Diploma": [14, 30], "PGDM": [19, 45]}}`
- **Requires Justification on Exception:** No

#### `APAAR_DOB_MISMATCH`

- **Meaning:** Date of birth differs from the registry
- **Scope:** `row`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** No

#### `APAAR_FORMAT`

- **Meaning:** Not exactly 12 digits
- **Scope:** `row`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** No

#### `APAAR_NAME_MISMATCH`

- **Meaning:** Fuzzy name match below threshold (default 85)
- **Scope:** `row`
- **Default Level:** `warning`
- **Implementation Status:** Active
- **Default Parameters:** `{"threshold": 85}`
- **Requires Justification on Exception:** No

#### `APAAR_NOT_FOUND`

- **Meaning:** ID does not exist in the registry
- **Scope:** `row`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** No

#### `APAAR_REQUIRED`

- **Meaning:** APAAR ID missing
- **Scope:** `row`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** No

#### `CATEGORY_CONFLICT`

- **Meaning:** NRI and foreign national both Yes
- **Scope:** `row`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** No

#### `COUNTRY_REQUIRED`

- **Meaning:** Foreign national is Yes but country is empty
- **Scope:** `row`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** No

#### `COURSE_NOT_APPROVED`

- **Meaning:** Course or branch not approved for this college
- **Scope:** `row`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** No

#### `DOB_INVALID`

- **Meaning:** Not a valid date, or in the future
- **Scope:** `row`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** No

#### `ENUM_INVALID`

- **Meaning:** Value not in the allowed list (gender, category, seat type, mode, Yes/No)
- **Scope:** `row`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `{"allowed_enums": {"gender": ["Female", "Male", "Other"], "reservation_category": ["EWS", "General", "OBC", "SC", "ST"], "seat_type": ["Regular", "Supernumerary"], "admission_mode": ["Direct second year", "JEE Main counselling", "Management quota", "NRI/OCI/foreign quota", "Other", "State counselling"], "nri": ["No", "Yes"], "oci": ["No", "Yes"], "foreign_national": ["No", "Yes"]}}`
- **Requires Justification on Exception:** No

#### `MODE_CATEGORY_MISMATCH`

- **Meaning:** NRI/OCI/foreign student not admitted through the NRI/OCI/foreign quota, or the reverse
- **Scope:** `row`
- **Default Level:** `warning`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** No

#### `NAME_FORMAT`

- **Meaning:** Name has digits or illegal characters
- **Scope:** `row`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** No

#### `NAME_REQUIRED`

- **Meaning:** Name missing
- **Scope:** `row`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** No

#### `SEAT_TYPE_NOT_APPROVED`

- **Meaning:** Supernumerary seat in a course with no supernumerary seats allowed
- **Scope:** `row`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** No

### 3.3 Course Quotas, Intake & Seat Declarations

#### `INTAKE_EXCEEDED`

- **Meaning:** Regular admitted is above approved intake. Message states the exact overshoot
- **Scope:** `course`
- **Default Level:** `exception`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** Yes

#### `SEAT_DECLARATION_MISMATCH`

- **Meaning:** Declared counts differ from uploaded student list. Blocks submit; college fixes either
- **Scope:** `course`
- **Default Level:** `error`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** No

#### `SUPERNUMERARY_EXCEEDED`

- **Meaning:** Supernumerary admitted is above the supernumerary seats AICTE allows
- **Scope:** `course`
- **Default Level:** `exception`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** Yes

### 3.4 Cross-College Duplicate Enrolments

#### `DUP_ACTIVE_OTHER_COLLEGE`

- **Meaning:** APAAR ID is active at another AICTE college this academic year. Both colleges notified. Resolved when one marks student withdrawn or transferred
- **Scope:** `cross`
- **Default Level:** `warning`
- **Implementation Status:** Active
- **Default Parameters:** `{"exclude_same_course": false}`
- **Requires Justification on Exception:** No

#### `DUP_SAME_COURSE_OTHER_COLLEGE`

- **Meaning:** Same APAAR ID in the same course and year at another college
- **Scope:** `cross`
- **Default Level:** `exception`
- **Implementation Status:** Active
- **Default Parameters:** `None`
- **Requires Justification on Exception:** Yes

### 3.5 Intelligent Anomaly Detection & ML

#### `ANOM_DOB_CLUSTER`

- **Meaning:** Many students share one date of birth (default 5 or more). Audience: aicte
- **Scope:** `anomaly`
- **Default Level:** `warning`
- **Implementation Status:** Active
- **Default Parameters:** `{"threshold_count": 5}`
- **Requires Justification on Exception:** No

#### `ANOM_ENROLMENT_JUMP`

- **Meaning:** Enrolment up more than a threshold (default 30%) against last year. Audience: aicte
- **Scope:** `anomaly`
- **Default Level:** `warning`
- **Implementation Status:** Active
- **Default Parameters:** `{"threshold_percent": 30.0}`
- **Requires Justification on Exception:** No

#### `ANOM_MODEL_SCORE`

- **Meaning:** IsolationForest score on college-course features flags this as unusual. Audience: aicte
- **Scope:** `anomaly`
- **Default Level:** `warning`
- **Implementation Status:** Active
- **Default Parameters:** `{"threshold_score": -0.05, "contamination": 0.08}`
- **Requires Justification on Exception:** No

#### `ANOM_NRI_SHARE`

- **Meaning:** NRI/OCI/foreign share unusually high (default over 25%). Audience: aicte
- **Scope:** `anomaly`
- **Default Level:** `warning`
- **Implementation Status:** Active
- **Default Parameters:** `{"threshold_percent": 25.0}`
- **Requires Justification on Exception:** No

#### `ANOM_SAME_ADMISSION_DAY`

- **Meaning:** Large share of students admitted on one day (default over 60%). Audience: aicte
- **Scope:** `anomaly`
- **Default Level:** `info`
- **Implementation Status:** Active
- **Default Parameters:** `{"threshold_percent": 60.0, "min_students": 5}`
- **Requires Justification on Exception:** No

#### `ANOM_SEQUENTIAL_APAAR`

- **Meaning:** Long runs of sequential APAAR IDs (default 10 or more). Audience: aicte
- **Scope:** `anomaly`
- **Default Level:** `warning`
- **Implementation Status:** Active
- **Default Parameters:** `{"threshold_run": 10}`
- **Requires Justification on Exception:** No

#### `ANOM_SUPERNUM_SHARE`

- **Meaning:** Supernumerary share unusually high (default over 15%). Audience: aicte
- **Scope:** `anomaly`
- **Default Level:** `warning`
- **Implementation Status:** Active
- **Default Parameters:** `{"threshold_percent": 15.0}`
- **Requires Justification on Exception:** No

---

## 4. Policy Configuration & Overrides

Administrators (`aicte_admin`) can customize rule behavior at runtime via `rule_config`
without deploying code changes:
- **Level Override**: Reassign a rule's severity level (e.g. promoting a `warning` to an `error`).
- **Parameter Customization**: Adjust numeric thresholds, admission date windows, age ranges, or fuzzy match ratios.
- **Enable/Disable**: Selectively disable specific rules for testing or policy shifts.

