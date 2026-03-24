# Requirements Document

## Introduction

The Weekly Report feature extends the existing Radar page in the gitxPost Web UI by adding a "Weekly Report" tab alongside the current "Daily Report" tab. This feature enables users to generate, view, and manage weekly summaries of X (Twitter) activity, including trending topics, recommended connections, highlighted tweets, action tracking, and account management suggestions. The feature reuses the existing daily report UI structure (left sidebar list + right detail panel) and Markdown rendering capabilities to minimize implementation complexity.

## Glossary

- **Radar_Page**: The existing page in the gitxPost Web UI that displays daily reports of AI-filtered tweets
- **Weekly_Report**: A Markdown document containing a weekly summary of X activity, stored in `xinfo/log/week/YYYY-MM-DD.md`
- **Daily_Report**: The existing feature that displays daily summaries of tweets
- **Tab_Switcher**: A UI component that allows users to toggle between Daily Report and Weekly Report views
- **Report_List**: A sidebar component displaying available reports sorted by date
- **Report_Detail**: The main content area displaying the full Markdown content of a selected report
- **Backend_API**: The FastAPI server at `web/api/server.py` that provides RESTful endpoints
- **Frontend_API**: The axios-based API client at `web/ui/src/api/xpost.js`
- **CLI_Command**: The existing `radar-weekly` command that generates weekly reports
- **Analysis_File**: A JSON file (`xinfo/log/day/YYYY-MM-DD_analysis.json`) containing analyzed tweet data
- **Actions_File**: A JSON file (`xinfo/log/actions.json`) tracking pending actions
- **Frontmatter**: YAML metadata at the beginning of Markdown files containing report metadata
- **Markdown_Renderer**: The marked.js library used to convert Markdown to HTML

## Requirements

### Requirement 1: Weekly Report Tab Navigation

**User Story:** As a user, I want to switch between daily and weekly reports using tabs, so that I can easily access different report types without navigating to separate pages.

#### Acceptance Criteria

1. THE Radar_Page SHALL display a Tab_Switcher with two options: "Daily Report" and "Weekly Report"
2. WHEN a user clicks the "Daily Report" tab, THE Radar_Page SHALL display the existing daily report interface
3. WHEN a user clicks the "Weekly Report" tab, THE Radar_Page SHALL display the weekly report interface
4. THE Tab_Switcher SHALL visually indicate which tab is currently active
5. WHEN switching tabs, THE Radar_Page SHALL preserve the current state of the inactive tab

### Requirement 2: Weekly Report List Display

**User Story:** As a user, I want to see a list of all available weekly reports, so that I can browse and select reports from different weeks.

#### Acceptance Criteria

1. WHEN the Weekly Report tab is active, THE Report_List SHALL display all weekly reports sorted by date in descending order
2. THE Report_List SHALL display each report with its date in MM/DD format
3. THE Report_List SHALL display each report's file size in kilobytes
4. WHEN a weekly report is for the current week, THE Report_List SHALL display a "Today" badge next to the date
5. WHEN no weekly reports exist, THE Report_List SHALL display an empty state message
6. THE Report_List SHALL visually highlight the currently selected report

### Requirement 3: Weekly Report Detail View

**User Story:** As a user, I want to view the full content of a weekly report, so that I can read the detailed analysis and recommendations.

#### Acceptance Criteria

1. WHEN a user selects a weekly report from the Report_List, THE Report_Detail SHALL display the full Markdown content
2. THE Report_Detail SHALL render Markdown using the Markdown_Renderer with the same preprocessing as daily reports
3. THE Report_Detail SHALL display report metadata from the Frontmatter including generation time and LLM model
4. THE Report_Detail SHALL apply the same styling as daily reports for consistent visual appearance
5. WHEN no report is selected, THE Report_Detail SHALL display an empty state with instructions

### Requirement 4: Weekly Report Generation

**User Story:** As a user, I want to generate a new weekly report, so that I can create an up-to-date summary of the week's activity.

#### Acceptance Criteria

1. THE Weekly Report interface SHALL display a "Generate Weekly Report" button
2. WHEN a user clicks the "Generate Weekly Report" button, THE Backend_API SHALL invoke the CLI_Command
3. WHILE report generation is in progress, THE button SHALL display "Generating..." and be disabled
4. WHEN report generation completes successfully, THE Report_List SHALL refresh to include the new report
5. WHEN report generation completes successfully, THE Radar_Page SHALL automatically select and display the new report
6. THE report generation process SHALL complete within 300 seconds or timeout

### Requirement 5: Backend API for Weekly Report Listing

**User Story:** As a developer, I want a backend endpoint to list all weekly reports, so that the frontend can display available reports.

#### Acceptance Criteria

1. THE Backend_API SHALL provide a GET endpoint at `/api/radar/weekly-reports`
2. WHEN the endpoint is called, THE Backend_API SHALL scan the `xinfo/log/week/` directory for Markdown files
3. THE Backend_API SHALL return a JSON response containing an array of report objects
4. THE report objects SHALL include date, absolute file path, and file size in bytes
5. THE report array SHALL be sorted by date in descending order

### Requirement 6: Backend API for Weekly Report Retrieval

**User Story:** As a developer, I want a backend endpoint to retrieve a specific weekly report, so that the frontend can display report details.

#### Acceptance Criteria

1. THE Backend_API SHALL provide a GET endpoint at `/api/radar/weekly-report/{date}`
2. WHEN the endpoint is called with a valid date, THE Backend_API SHALL read the corresponding Markdown file
3. THE Backend_API SHALL parse the Frontmatter and separate it from the Markdown body
4. THE Backend_API SHALL return a JSON response containing the date, frontmatter object, and markdown content
5. WHEN the requested report does not exist, THE Backend_API SHALL return HTTP 404 with an error message

### Requirement 7: Backend API for Weekly Report Generation

**User Story:** As a developer, I want a backend endpoint to trigger weekly report generation, so that the frontend can initiate report creation.

#### Acceptance Criteria

1. THE Backend_API SHALL provide a POST endpoint at `/api/radar/weekly`
2. WHEN the endpoint is called, THE Backend_API SHALL execute the CLI_Command with a 300-second timeout
3. THE Backend_API SHALL return the CLI_Command output as JSON
4. WHEN the CLI_Command times out, THE Backend_API SHALL return HTTP 504 with a timeout error message
5. THE Backend_API SHALL use the existing process lock to prevent concurrent report generation

### Requirement 8: Frontend API Functions

**User Story:** As a developer, I want frontend API functions for weekly reports, so that Vue components can easily interact with the backend.

#### Acceptance Criteria

1. THE Frontend_API SHALL provide a `getWeeklyReports()` function that calls GET `/api/radar/weekly-reports`
2. THE Frontend_API SHALL provide a `getWeeklyReport(date)` function that calls GET `/api/radar/weekly-report/{date}`
3. THE Frontend_API SHALL provide a `runWeekly(config)` function that calls POST `/api/radar/weekly`
4. THE Frontend_API functions SHALL use the same axios instance and error handling as existing functions
5. THE `runWeekly()` function SHALL accept an optional config parameter for request cancellation

### Requirement 9: Weekly Report Markdown Parsing

**User Story:** As a developer, I want to parse weekly report Markdown files, so that the backend can extract structured data for the frontend.

#### Acceptance Criteria

1. THE Backend_API SHALL provide a `_parse_weekly_report()` function
2. WHEN a Markdown file starts with `---`, THE function SHALL extract YAML frontmatter
3. THE function SHALL parse frontmatter key-value pairs and return them as a dictionary
4. THE function SHALL return the Markdown body content after the closing `---`
5. WHEN no frontmatter exists, THE function SHALL return an empty frontmatter dictionary and the full content as markdown

### Requirement 10: Error Handling for Missing Analysis Files

**User Story:** As a user, I want clear error messages when prerequisites are missing, so that I know what actions to take before generating a weekly report.

#### Acceptance Criteria

1. WHEN the CLI_Command fails due to missing Analysis_File, THE Backend_API SHALL return an error response with `ok: false`
2. THE error response SHALL include a descriptive error message indicating the missing file
3. WHEN the frontend receives this error, THE Radar_Page SHALL display a toast notification
4. THE toast notification SHALL instruct the user to run "Radar Analysis" before generating a weekly report
5. THE "Generate Weekly Report" button SHALL return to its normal state after the error

### Requirement 11: Error Handling for Missing API Keys

**User Story:** As a user, I want to be notified when API keys are missing, so that I can configure them before attempting report generation.

#### Acceptance Criteria

1. WHEN the CLI_Command fails due to missing LLM API key, THE Backend_API SHALL return an error response
2. THE error response SHALL include a message indicating the API key is not configured
3. WHEN the frontend receives this error, THE Radar_Page SHALL display a toast notification
4. THE toast notification SHALL inform the user that the LLM API key is not configured
5. THE notification SHALL remain visible long enough for the user to read and understand the issue

### Requirement 12: Error Handling for Generation Timeout

**User Story:** As a user, I want to be notified when report generation times out, so that I can retry or investigate the issue.

#### Acceptance Criteria

1. WHEN the CLI_Command exceeds the 300-second timeout, THE Backend_API SHALL terminate the process
2. THE Backend_API SHALL return HTTP 504 with a timeout error message
3. WHEN the frontend receives a timeout error, THE Radar_Page SHALL display a toast notification
4. THE toast notification SHALL inform the user that report generation timed out
5. THE "Generate Weekly Report" button SHALL return to its normal state allowing retry

### Requirement 13: Error Handling for Nonexistent Reports

**User Story:** As a user, I want clear feedback when attempting to view a report that doesn't exist, so that I understand why content isn't displayed.

#### Acceptance Criteria

1. WHEN a user attempts to view a nonexistent weekly report, THE Backend_API SHALL return HTTP 404
2. THE error response SHALL include the requested date in the error message
3. WHEN the frontend receives a 404 error, THE Radar_Page SHALL display a toast notification
4. THE toast notification SHALL inform the user that the report for the specified date does not exist
5. THE Report_Detail SHALL display an empty state

### Requirement 14: UI State Management for Weekly Reports

**User Story:** As a developer, I want proper state management for weekly reports, so that the UI remains responsive and consistent.

#### Acceptance Criteria

1. THE Radar_Page SHALL maintain separate state variables for weekly reports: `weeklyReports`, `weeklyReport`, `weeklyLoading`, `weeklyGenerating`
2. WHEN loading the weekly report list, THE `weeklyLoading` state SHALL be true
3. WHEN generating a weekly report, THE `weeklyGenerating` state SHALL be true
4. THE Radar_Page SHALL clear selected tweet state when switching between tabs
5. THE Radar_Page SHALL preserve the selected report date when switching tabs and returning

### Requirement 15: Weekly Report Markdown Rendering

**User Story:** As a user, I want weekly reports to be rendered with proper formatting, so that the content is readable and visually appealing.

#### Acceptance Criteria

1. THE Markdown_Renderer SHALL use the same preprocessing function as daily reports
2. THE preprocessing function SHALL convert bullet points (• and ·) to Markdown list items
3. THE preprocessing function SHALL convert emoji-prefixed lines to H2 headings
4. THE Markdown_Renderer SHALL apply GitHub Flavored Markdown (GFM) with line breaks enabled
5. THE rendered HTML SHALL apply the same CSS styling as daily reports for consistency

### Requirement 16: Pipeline Integration for Weekly Reports

**User Story:** As a developer, I want weekly report generation to be available in the pipeline API, so that automated workflows can include weekly reports.

#### Acceptance Criteria

1. THE Backend_API pipeline endpoint SHALL accept "weekly" as a valid step
2. WHEN the pipeline includes a "weekly" step, THE Backend_API SHALL execute the CLI_Command
3. THE pipeline SHALL use the same 300-second timeout as the standalone endpoint
4. THE pipeline response SHALL include the weekly report generation result
5. WHEN weekly report generation fails, THE pipeline SHALL stop and return the error

### Requirement 17: Weekly Report File Structure Validation

**User Story:** As a developer, I want to validate weekly report file structure, so that the system handles malformed files gracefully.

#### Acceptance Criteria

1. THE Backend_API SHALL validate that weekly report files are valid UTF-8 encoded text
2. WHEN a file cannot be read, THE Backend_API SHALL return an appropriate error response
3. THE `_parse_weekly_report()` function SHALL handle files without frontmatter
4. THE `_parse_weekly_report()` function SHALL handle malformed YAML frontmatter
5. WHEN parsing fails, THE Backend_API SHALL return the raw content as markdown with an empty frontmatter

### Requirement 18: Weekly Report Loading Performance

**User Story:** As a user, I want weekly reports to load quickly, so that I can efficiently browse through multiple reports.

#### Acceptance Criteria

1. THE Backend_API SHALL read weekly report files directly from disk without caching
2. THE Report_List SHALL display a loading skeleton while fetching the list
3. THE Report_Detail SHALL display a loading skeleton while fetching report content
4. THE loading skeletons SHALL match the visual style of daily report loading states
5. THE Radar_Page SHALL cancel pending requests when switching tabs or selecting a different report

### Requirement 19: Weekly Report Date Formatting

**User Story:** As a user, I want report dates to be displayed in a consistent and readable format, so that I can easily identify reports by date.

#### Acceptance Criteria

1. THE Report_List SHALL display dates in MM/DD format for space efficiency
2. THE Report_Detail SHALL display the full date from the frontmatter in the metadata section
3. THE date formatting function SHALL handle YYYY-MM-DD format input
4. THE date formatting function SHALL be reused from the existing daily report implementation
5. THE "Today" badge logic SHALL correctly identify reports from the current week

### Requirement 20: Weekly Report Empty States

**User Story:** As a user, I want helpful empty state messages, so that I understand what to do when no reports are available.

#### Acceptance Criteria

1. WHEN no weekly reports exist, THE Report_List SHALL display an icon and message "No weekly reports"
2. WHEN no report is selected, THE Report_Detail SHALL display an icon and message "Select a weekly report to view"
3. THE empty state SHALL include a hint to click "Generate Weekly Report" to create the first report
4. THE empty state styling SHALL match the daily report empty states
5. THE empty state icons SHALL use the same SVG style as daily reports
