import React, { useState } from "react";
import {
  Button,
  IconButton,
  Link,
  Icon,
  Badge,
  FlagBadge,
  RoleBadge,
  Tag,
  Alert,
  ToastProvider,
  useToast,
  Tooltip,
  Input,
  Textarea,
  Select,
  Radio,
  Checkbox,
  Switch,
  DatePicker,
  FileUpload,
  OtpInput,
  FormField,
  ErrorSummary,
  Navbar,
  Sidebar,
  Breadcrumb,
  Tabs,
  Stepper,
  Pagination,
  Footer,
  Card,
  CardHeader,
  CardTitle,
  CardBody,
  CardFooter,
  Accordion,
  Modal,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  EmptyState,
  Spinner,
  Skeleton,
  Progress,
} from "../components/ux4g";

function DevComponentsContent() {
  const { addToast } = useToast();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [otpValue, setOtpValue] = useState("1234");
  const [currentPage, setCurrentPage] = useState(2);
  const [activeTab, setActiveTab] = useState("tab1");
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const demoErrors = [
    { fieldId: "demo-input-error", message: "Student APAAR ID must be exactly 12 digits." },
    { fieldId: "demo-select-error", message: "Please select an approved course." },
  ];

  return (
    <div className="min-h-screen ux4g-bg-neutral-soft ux4g-text-neutral-primary pb-20">
      {/* Dev Page Top Banner */}
      <div className="ux4g-bg-primary-stronger ux4g-text-white px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <span>UX4G Component Showcase & State Catalog</span>
            <span className="text-xs ux4g-bg-primary-strong px-2 py-0.5 rounded font-mono uppercase">
              Dev Only
            </span>
          </h1>
          <p className="text-xs opacity-90 mt-0.5">
            Living catalog of all 28 UX4G wrappers verifying Default, Hover, Focus, Disabled,
            Error, and Loading states.
          </p>
        </div>
        <Link to="/" className="text-inherit underline text-sm">
          Back to Home
        </Link>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-12">
        {/* =================================================================== */}
        {/* 1. Core: Buttons */}
        {/* =================================================================== */}
        <section className="ux4g-bg-neutral-elevated p-6 rounded-xl border ux4g-border-neutral-subtle space-y-4">
          <h2 className="text-lg font-bold border-b pb-2 ux4g-text-neutral-primary">
            1. Core: Button & Icon Button
          </h2>
          <div className="space-y-4">
            <div>
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase mb-2">Variants</p>
              <div className="flex flex-wrap items-center gap-3">
                <Button variant="primary">Primary Button</Button>
                <Button variant="outline-primary">Outline Primary</Button>
                <Button variant="tonal-primary">Tonal Primary</Button>
                <Button variant="danger">Danger Button</Button>
                <Button variant="outline-danger">Outline Danger</Button>
                <Button variant="text-primary">Text Primary</Button>
                <Button variant="outline-neutral">Outline Neutral</Button>
                <Button variant="text-neutral">Text Neutral</Button>
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase mb-2">Sizes</p>
              <div className="flex flex-wrap items-center gap-3">
                <Button size="s" variant="primary">Small (s)</Button>
                <Button size="m" variant="primary">Medium (m)</Button>
                <Button size="l" variant="primary">Large (l)</Button>
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase mb-2">States</p>
              <div className="flex flex-wrap items-center gap-3">
                <Button variant="primary">Default</Button>
                <Button variant="primary" disabled>Disabled State</Button>
                <Button variant="primary" isLoading loadingText="Saving...">Loading State</Button>
                <Button variant="danger" isLoading>Loading Danger</Button>
                <Button
                  variant="primary"
                  leftIcon={<Icon name="add" size="sm" color="inherit" aria-hidden="true" />}
                >
                  With Left Icon
                </Button>
                <IconButton
                  variant="primary"
                  size="md"
                  icon={<Icon name="search" size="sm" color="inherit" aria-hidden="true" />}
                  aria-label="Search"
                />
                <IconButton
                  variant="outline-primary"
                  size="md"
                  icon={<Icon name="settings" size="sm" color="inherit" aria-hidden="true" />}
                  aria-label="Settings"
                />
              </div>
            </div>
          </div>
        </section>

        {/* =================================================================== */}
        {/* 2. Core: Link & Icon */}
        {/* =================================================================== */}
        <section className="ux4g-bg-neutral-elevated p-6 rounded-xl border ux4g-border-neutral-subtle space-y-4">
          <h2 className="text-lg font-bold border-b pb-2 ux4g-text-neutral-primary">
            2. Core: Link & Material Symbols Icon
          </h2>
          <div className="space-y-4">
            <div>
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase mb-2">Links</p>
              <div className="flex items-center gap-6">
                <Link to="/dev/components" size="md">Router Link (Default)</Link>
                <Link to="/dev/components" size="sm">Small Router Link</Link>
                <Link href="https://example.com" isExternal size="md">External Link ↗</Link>
                <Link href="#" variant="neutral">Neutral Text Link</Link>
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase mb-2">
                Material Symbols Icons (UX4G embedded font)
              </p>
              <div className="flex items-center gap-6 ux4g-text-neutral-primary">
                <div className="flex items-center gap-2">
                  <Icon name="check_circle" size="xs" color="success" />
                  <span className="text-xs">xs (14px)</span>
                </div>
                <div className="flex items-center gap-2">
                  <Icon name="info" size="sm" color="info" />
                  <span className="text-xs">sm (16px)</span>
                </div>
                <div className="flex items-center gap-2">
                  <Icon name="warning" size="md" color="warning" />
                  <span className="text-xs">md (20px)</span>
                </div>
                <div className="flex items-center gap-2">
                  <Icon name="error" size="lg" color="error" />
                  <span className="text-xs">lg (24px)</span>
                </div>
                <div className="flex items-center gap-2">
                  <Icon name="school" size="xl" color="primary" />
                  <span className="text-xs">xl (32px)</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* =================================================================== */}
        {/* 3. Core: Badges, FlagBadges & Tags */}
        {/* =================================================================== */}
        <section className="ux4g-bg-neutral-elevated p-6 rounded-xl border ux4g-border-neutral-subtle space-y-4">
          <h2 className="text-lg font-bold border-b pb-2 ux4g-text-neutral-primary">
            3. Core: Badges, FlagBadge (SPEC §19) & Tags
          </h2>
          <div className="space-y-4">
            <div>
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase mb-2">Standard Badges</p>
              <div className="flex flex-wrap items-center gap-3">
                <Badge variant="primary">Primary</Badge>
                <Badge variant="success">Success</Badge>
                <Badge variant="warning">Warning</Badge>
                <Badge variant="danger">Danger</Badge>
                <Badge variant="info">Info</Badge>
                <Badge variant="neutral">Neutral</Badge>
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase mb-2">
                FlagBadge (SPEC §19 / DECISIONS.md Difference 6)
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <FlagBadge level="error" count={4} />
                <FlagBadge level="exception" count={2} />
                <FlagBadge level="warning" count={7} />
                <FlagBadge level="info" count={1} />
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase mb-2">Role Badges</p>
              <div className="flex flex-wrap items-center gap-3">
                <RoleBadge role="college_admin" />
                <RoleBadge role="college_staff" />
                <RoleBadge role="aicte_officer" />
                <RoleBadge role="aicte_admin" />
                <RoleBadge role="verifier" />
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase mb-2">Tags</p>
              <div className="flex flex-wrap items-center gap-3">
                <Tag variant="tonal" color="brand">Tonal Brand</Tag>
                <Tag variant="filled" color="success">Filled Success</Tag>
                <Tag variant="outline" color="warning">Outline Warning</Tag>
                <Tag variant="text" color="error">Text Error</Tag>
                <Tag variant="tonal" color="neutral" onDismiss={() => {}}>
                  Dismissible Tag
                </Tag>
              </div>
            </div>
          </div>
        </section>

        {/* =================================================================== */}
        {/* 4. Core: Alerts, Toasts & Tooltips */}
        {/* =================================================================== */}
        <section className="ux4g-bg-neutral-elevated p-6 rounded-xl border ux4g-border-neutral-subtle space-y-4">
          <h2 className="text-lg font-bold border-b pb-2 ux4g-text-neutral-primary">
            4. Core: Alerts, Toasts & Tooltips
          </h2>
          <div className="space-y-4">
            <div className="space-y-2">
              <Alert variant="info" title="Information Note" onDismiss={() => {}}>
                APAAR registry lookups are simulated in demo mode.
              </Alert>
              <Alert variant="success" title="Success" onDismiss={() => {}}>
                All 120 student records verified and accepted into the central repository.
              </Alert>
              <Alert variant="warning" title="Warning" onDismiss={() => {}}>
                Regular admission count approaches approved intake threshold.
              </Alert>
              <Alert variant="error" title="Validation Blocker" onDismiss={() => {}}>
                Submit gate blocked: 3 open format errors require resolution.
              </Alert>
            </div>

            <div className="pt-2 flex items-center gap-6">
              <Button
                variant="outline-primary"
                onClick={() =>
                  addToast({
                    variant: "success",
                    title: "Toast Notification",
                    message: "A new student draft was successfully saved.",
                  })
                }
              >
                Trigger Sample Toast
              </Button>

              <Tooltip content="Tooltip showing helpful context on hover or focus">
                <Button variant="outline-neutral">Hover / Focus for Tooltip</Button>
              </Tooltip>
            </div>
          </div>
        </section>

        {/* =================================================================== */}
        {/* 5. Forms: FormField, ErrorSummary & All Inputs */}
        {/* =================================================================== */}
        <section className="ux4g-bg-neutral-elevated p-6 rounded-xl border ux4g-border-neutral-subtle space-y-6">
          <h2 className="text-lg font-bold border-b pb-2 ux4g-text-neutral-primary">
            5. Forms: FormField, ErrorSummary, Inputs & Controls
          </h2>

          <ErrorSummary errors={demoErrors} autoFocus={false} />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FormField
              id="demo-input-default"
              label="Student Name"
              hint="Letters, spaces, dots, hyphens only"
            >
              <Input placeholder="e.g. Ramesh Kumar" />
            </FormField>

            <FormField
              id="demo-input-error"
              label="APAAR ID"
              required
              error="Must be exactly 12 numeric digits"
            >
              <Input defaultValue="12345" state="error" />
            </FormField>

            <FormField
              id="demo-select-error"
              label="Approved Course"
              required
              error="Please select an approved course"
            >
              <Select
                state="error"
                options={[
                  { value: "", label: "Select course..." },
                  { value: "cse", label: "Computer Science & Engineering (UG)" },
                  { value: "ece", label: "Electronics & Communication (UG)" },
                ]}
              />
            </FormField>

            <FormField
              id="demo-datepicker"
              label="Date of Birth"
              hint="Must be in the past (YYYY-MM-DD)"
            >
              <DatePicker defaultValue="2005-04-12" />
            </FormField>

            <div className="md:col-span-2">
              <FormField id="demo-textarea" label="Justification Note">
                <Textarea placeholder="Explain real-world compliance condition..." rows={3} />
              </FormField>
            </div>

            <div className="space-y-3">
              <p className="text-sm font-semibold">Toggles & Checks</p>
              <div className="flex flex-col gap-2">
                <Checkbox label="I confirm the declared seat numbers are accurate" defaultChecked />
                <Checkbox label="Disabled checkbox" disabled />
                <Radio name="demo-radio" label="Regular Seat Mode" defaultChecked />
                <Radio name="demo-radio" label="Supernumerary Quota" />
                <Switch label="Real-time validation updates" defaultChecked />
              </div>
            </div>

            <div>
              <p className="text-sm font-semibold mb-2">OTP 6-Digit Box (Auto-advance & Paste)</p>
              <OtpInput value={otpValue} onChange={setOtpValue} />
              <p className="text-xs ux4g-text-neutral-tertiary mt-1">Current value: {otpValue}</p>
            </div>

            <div className="md:col-span-2">
              <FileUpload
                id="demo-file-upload"
                accept=".csv,.xlsx"
                selectedFile={selectedFile}
                onFileSelect={(f) => setSelectedFile(f)}
                onFileClear={() => setSelectedFile(null)}
                hint="Upload CSV file according to the AICTE student intake template"
              />
            </div>
          </div>
        </section>

        {/* =================================================================== */}
        {/* 6. Navigation: Breadcrumb, Tabs, Stepper & Pagination */}
        {/* =================================================================== */}
        <section className="ux4g-bg-neutral-elevated p-6 rounded-xl border ux4g-border-neutral-subtle space-y-6">
          <h2 className="text-lg font-bold border-b pb-2 ux4g-text-neutral-primary">
            6. Navigation: Breadcrumbs, Tabs, Stepper & Pagination
          </h2>

          <div className="space-y-6">
            <div>
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase mb-2">Navbar Preview</p>
              <div className="border ux4g-border-neutral-subtle rounded-lg overflow-hidden">
                <Navbar
                  brand={<span className="font-bold text-base ux4g-text-brand-primary">EduTrace</span>}
                  items={[
                    { label: "Overview", href: "/dev/components", active: true },
                    { label: "Students", href: "/dev/components" },
                    { label: "Reports", href: "/dev/components" },
                  ]}
                  rightContent={
                    <Button size="s" variant="primary">
                      Action
                    </Button>
                  }
                />
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase mb-2">Sidebar Preview</p>
              <div className="border ux4g-border-neutral-subtle rounded-lg overflow-hidden max-w-xs">
                <Sidebar
                  sections={[
                    {
                      title: "College Workspace",
                      items: [
                        { id: "s1", label: "Dashboard", href: "/dev/components", icon: "dashboard", active: true },
                        { id: "s2", label: "Students", href: "/dev/components", icon: "people", badge: <Badge variant="primary">120</Badge> },
                        { id: "s3", label: "Upload CSV", href: "/dev/components", icon: "upload" },
                      ],
                    },
                  ]}
                />
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase mb-2">Breadcrumb</p>
              <Breadcrumb
                items={[
                  { label: "Home", href: "/" },
                  { label: "College Portal", href: "/college/dashboard" },
                  { label: "Student List" },
                ]}
              />
            </div>

            <div>
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase mb-2">Stepper</p>
              <Stepper
                currentStep={currentStep}
                steps={[
                  { title: "Lookup Institution", description: "AICTE ID search" },
                  { title: "OTP Verification", description: "Official contact OTP" },
                  { title: "Signatory Claim", description: "Upload authorization" },
                  { title: "Pending Approval", description: "AICTE review queue" },
                ]}
              />
              <div className="mt-3 flex gap-2">
                <Button
                  size="s"
                  variant="outline-neutral"
                  disabled={currentStep === 0}
                  onClick={() => setCurrentStep((s) => Math.max(0, s - 1))}
                >
                  Previous Step
                </Button>
                <Button
                  size="s"
                  variant="primary"
                  disabled={currentStep === 3}
                  onClick={() => setCurrentStep((s) => Math.min(3, s + 1))}
                >
                  Next Step
                </Button>
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase mb-2">Tabs</p>
              <Tabs
                activeId={activeTab}
                onChange={setActiveTab}
                items={[
                  {
                    id: "tab1",
                    label: "Student Records",
                    badge: <Badge variant="primary">120</Badge>,
                    content: <p className="text-sm">Content of tab 1: All uploaded student records.</p>,
                  },
                  {
                    id: "tab2",
                    label: "Validation Flags",
                    badge: <Badge variant="danger">4</Badge>,
                    content: <p className="text-sm">Content of tab 2: Validation exceptions and warnings.</p>,
                  },
                  {
                    id: "tab3",
                    label: "Seat Declaration",
                    content: <p className="text-sm">Content of tab 3: Comparison of intake vs enrolment.</p>,
                  },
                ]}
              />
            </div>

            <div>
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase mb-2">Pagination</p>
              <Pagination
                currentPage={currentPage}
                totalPages={8}
                onPageChange={setCurrentPage}
              />
            </div>
          </div>
        </section>

        {/* =================================================================== */}
        {/* 7. Content: Card, Accordion, Modal, Table, Empty State & Progress */}
        {/* =================================================================== */}
        <section className="ux4g-bg-neutral-elevated p-6 rounded-xl border ux4g-border-neutral-subtle space-y-6">
          <h2 className="text-lg font-bold border-b pb-2 ux4g-text-neutral-primary">
            7. Content: Card, Accordion, Modal, Table, EmptyState & Progress
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card variant="solid">
              <CardHeader>
                <CardTitle>Solid Card with Header</CardTitle>
              </CardHeader>
              <CardBody>
                <p className="text-sm ux4g-text-neutral-secondary">
                  Cards represent bounded surfaces conforming to UX4G elevation and radius standards.
                </p>
              </CardBody>
              <CardFooter>
                <span className="text-xs ux4g-text-neutral-tertiary">Last updated: Today</span>
                <Button size="s" variant="primary">Action</Button>
              </CardFooter>
            </Card>

            <div className="space-y-4">
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase">Accordion</p>
              <Accordion
                items={[
                  {
                    id: "acc-1",
                    title: "What is an APAAR ID?",
                    content: "Automated Permanent Academic Account Registry ID: a 12-digit unique national ID for students.",
                  },
                  {
                    id: "acc-2",
                    title: "What constitutes over-admission?",
                    content: "Over-admission occurs when regular admissions exceed AICTE-approved course intake.",
                  },
                ]}
              />

              <div className="pt-2">
                <Button variant="outline-primary" onClick={() => setIsModalOpen(true)}>
                  Open Sample Modal Dialog
                </Button>
                <Modal
                  isOpen={isModalOpen}
                  onClose={() => setIsModalOpen(false)}
                  title="Confirm Final Submission"
                  footer={
                    <>
                      <Button variant="outline-neutral" onClick={() => setIsModalOpen(false)}>
                        Cancel
                      </Button>
                      <Button variant="primary" onClick={() => setIsModalOpen(false)}>
                        Confirm & Lock
                      </Button>
                    </>
                  }
                >
                  <p>
                    Are you sure you want to submit? Once submitted, student records are locked
                    and cross-college duplicate checks will execute automatically.
                  </p>
                </Modal>
              </div>
            </div>

            <div className="md:col-span-2 space-y-2">
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase">UX4G Table</p>
              <Table size="m" columnDividers zebra>
                <TableHeader>
                  <TableRow>
                    <TableHead sortDirection="ascending">APAAR ID</TableHead>
                    <TableHead>Student Name</TableHead>
                    <TableHead>Course</TableHead>
                    <TableHead>Seat Type</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow>
                    <TableCell className="font-mono">999988887777</TableCell>
                    <TableCell className="font-medium">Aaditya Patil</TableCell>
                    <TableCell>B.Tech CSE</TableCell>
                    <TableCell>Regular</TableCell>
                    <TableCell><FlagBadge level="error" count={1} /></TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-mono">888877776666</TableCell>
                    <TableCell className="font-medium">Priya Sharma</TableCell>
                    <TableCell>B.Tech ECE</TableCell>
                    <TableCell>Supernumerary</TableCell>
                    <TableCell><FlagBadge level="info" label="Clean" /></TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>

            <div>
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase mb-2">Empty State</p>
              <EmptyState
                title="No queries pending"
                description="Your institution has addressed all reviewer enquiries."
                action={<Button size="s" variant="outline-primary">Check History</Button>}
              />
            </div>

            <div className="space-y-4">
              <p className="text-xs font-semibold ux4g-text-neutral-tertiary uppercase">
                Progress, Spinners & Skeletons
              </p>
              <Progress value={65} max={100} label="Intake Seat Utilisation" showPercent />
              <Progress value={90} max={100} variant="danger" label="Quota Alert" showPercent />

              <div className="flex items-center gap-4 pt-2">
                <Spinner size="xs" />
                <Spinner size="sm" variant="inverse" />
                <Spinner size="md" variant="primary" />
                <Spinner size="lg" variant="danger" />
              </div>

              <div className="space-y-2 pt-2">
                <Skeleton height={20} width="60%" />
                <Skeleton height={14} width="100%" />
                <Skeleton height={14} width="85%" />
              </div>
            </div>
          </div>
        </section>
      </div>

      <Footer />
    </div>
  );
}

export function DevComponentsPage() {
  return (
    <ToastProvider>
      <DevComponentsContent />
    </ToastProvider>
  );
}
