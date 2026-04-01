# Implementation Plan: X Article 工作站用户体验优化

## Overview

This implementation plan transforms the article workflow from a fragmented multi-step process into a streamlined one-click experience with enhanced feedback, optimized layout, and improved editing capabilities. The implementation follows priority levels (P0 → P1 → P2) and includes both frontend Vue components and backend FastAPI endpoints.

## Tasks

### Phase 1: Backend Foundation (P0)

- [x] 1. Implement auto-generate API endpoint
  - Create POST `/api/articles/{article_id}/auto-generate` endpoint in `web/api/server.py`
  - Accept `style` parameter (zara/tech/fun, default: zara)
  - Implement `_auto_generate_background()` async function to orchestrate outline → content workflow
  - Pass style parameter to xpost init command
  - Add background task execution using asyncio
  - Implement process cancellation tracking with global state
  - Save style to article metadata
  - _Requirements: FR-1.1, FR-1.1.1, AC-1_

- [x] 2. Implement image upload API endpoint
  - Create POST `/api/articles/{article_id}/images` endpoint
  - Accept multipart/form-data file upload
  - Validate file type (image/png, image/jpeg, image/gif, image/webp)
  - Save to `xinfo/log/articles/{article_id}/images/` directory
  - Generate unique filename with timestamp
  - Update article metadata with image list
  - Return image URL and markdown syntax
  - _Requirements: FR-4.1.1, AC-4_

- [ ] 2. Enhance WebSocket progress events
  - Add `article_outline_progress` event with progress percentage (0-100)
  - Add `article_content_progress` event with section tracking
  - Modify existing xpost subprocess calls to emit progress updates
  - Update `_broadcast_article_update()` to handle new event types
  - _Requirements: FR-1.3, FR-3.1, FR-3.3_

- [x] 3. Implement cancellation API endpoint
  - Create POST `/api/articles/{article_id}/cancel` endpoint
  - Implement `_kill_active_xpost()` function to terminate subprocess
  - Track active generation processes in global dictionary
  - Return article to editable state after cancellation
  - _Requirements: FR-1.1 (user can interrupt)_

- [ ]* 4. Write backend unit tests
  - Test auto-generate workflow with different styles in `web/api/test_workflow_api.py`
  - Test image upload with valid and invalid files
  - Test cancellation preserves partial content
  - Test WebSocket event broadcasting sequence
  - Test error handling for failed generation
  - _Requirements: FR-1.1, FR-1.1.1, FR-4.1.1_

### Phase 2: Core Frontend Components (P0)

- [x] 5. Create WorkflowOrchestrator composable
  - Create `web/ui/src/composables/useWorkflowOrchestrator.js`
  - Implement state management (currentStep, progress, canCancel, selectedStyle)
  - Implement `startAutoGeneration(style)` method calling `/auto-generate` endpoint with style parameter
  - Implement `cancelGeneration()` method
  - Add WebSocket event listeners for progress updates
  - _Requirements: FR-1.1, FR-1.1.1, AC-1_

- [ ]* 6. Write property test for WorkflowOrchestrator
  - **Property 1: Auto-Generation Workflow Completion**
  - **Validates: Requirements FR-1.1, AC-1, FR-1.3, FR-3.3**
  - Test that outline → content sequence completes for any valid article
  - Verify progress increases monotonically from 0 to 100
  - _Requirements: FR-1.1_

- [x] 7. Create CompactHeader component
  - Create `web/ui/src/components/CompactHeader.vue`
  - Implement inline title editing with auto-save on blur
  - Add style selector dropdown (zara/tech/fun)
  - Add step badge and status badge displays
  - Reduce header height to ~60px
  - Add back button navigation
  - Save selected style to article metadata
  - Remember last selected style in localStorage
  - _Requirements: FR-1.1.1, FR-2.1, AC-1, AC-2_

- [x] 8. Create FloatingActionPanel component
  - Create `web/ui/src/components/FloatingActionPanel.vue`
  - Position fixed at bottom-right with z-index layering
  - Add conditional rendering for "一键生成" vs "发布文章" buttons
  - Display save status indicator
  - Add preview toggle button
  - _Requirements: FR-2.3, AC-2_

- [x] 9. Create ProgressIndicator component
  - Create `web/ui/src/components/ProgressIndicator.vue`
  - Implement progress bar with percentage display
  - Add dynamic status messages based on current step
  - Show cancel button when `canCancel` is true
  - Add smooth progress animations
  - _Requirements: FR-3.1, AC-3_

- [ ] 10. Checkpoint - Verify core workflow
  - Test one-click generation end-to-end in browser
  - Verify progress updates display correctly
  - Ensure cancellation works properly
  - Ensure all tests pass, ask the user if questions arise.

### Phase 3: Enhanced Editor Features (P0)

- [x] 11. Add auto-save to MarkdownEditor
  - Modify `web/ui/src/components/MarkdownEditor.vue`
  - Implement 3-second debounce using lodash.debounce or custom implementation
  - Call PUT `/api/articles/{id}` on content change
  - Track save status (saved/saving/unsaved/error)
  - Display "已自动保存 于 HH:MM" message
  - _Requirements: FR-4.2, AC-4_

- [x] 11.5 Add image insertion to MarkdownEditor
  - Add drag & drop event handlers for images
  - Add toolbar button for image file selection
  - Add paste event handler for clipboard images
  - Implement `uploadImage()` method calling POST `/api/articles/{id}/images`
  - Show upload progress indicator
  - Auto-insert markdown syntax after successful upload
  - Support PNG, JPG, GIF, WebP formats
  - _Requirements: FR-4.1.1, AC-4_

- [ ]* 12. Write property test for auto-save
  - **Property 5: Keyboard Shortcuts and Auto-Save**
  - **Validates: Requirements FR-4.1, FR-4.2, AC-4**
  - Test auto-save triggers after exactly 3 seconds for any content change
  - Verify no save occurs before 3 seconds
  - _Requirements: FR-4.2_

- [x] 13. Implement keyboard shortcuts
  - Add keyboard event listeners in ArticleEditorPage.vue
  - Implement Cmd/Ctrl+S for manual save
  - Implement Cmd/Ctrl+P for preview toggle
  - Implement Cmd/Ctrl+Enter for generate/publish action
  - Prevent default browser behavior for captured shortcuts
  - _Requirements: FR-4.1, AC-4_

- [x] 14. Integrate components into ArticleEditorPage
  - Modify `web/ui/src/views/ArticleEditorPage.vue`
  - Replace existing header with CompactHeader component
  - Pass style prop to CompactHeader
  - Add FloatingActionPanel component
  - Add ProgressIndicator component with conditional rendering
  - Wire up WorkflowOrchestrator composable with style parameter
  - Connect WebSocket listeners to component state
  - _Requirements: FR-1.1, FR-1.1.1, FR-2.1, FR-2.3, FR-3.1, FR-4.1.1_

- [ ]* 14.5 End-to-end test - One-click generation core workflow
  - Use Playwright to test complete workflow
  - Test: Create article → Select style → Click "一键生成" → Wait for completion → Verify content generated
  - Test: Generation process → Click "取消" → Verify cancellation works
  - Test: Auto-save functionality → Edit content → Wait 3 seconds → Verify saved
  - Test: Image insertion → Drag image → Verify upload and markdown insertion
  - _Requirements: FR-1.1, FR-1.1.1, FR-4.1.1, FR-4.2, AC-1, AC-4_

### Phase 4: Preview Mode Enhancement (P1)

- [ ] 15. Implement preview mode switching
  - Add preview mode state to ArticleEditorPage: 'hidden' | 'side' | 'fullscreen'
  - Implement toggle logic cycling through modes
  - Add CSS classes for each mode with responsive layouts
  - Make preview collapsible with smooth transitions
  - Persist preview mode preference in localStorage
  - _Requirements: FR-2.2, AC-2_

- [ ]* 16. Write property test for preview mode
  - **Property 3: Preview Mode State Transitions**
  - **Validates: Requirements FR-2.2**
  - Test preview mode cycles correctly through all states
  - Verify state persists across page reloads
  - _Requirements: FR-2.2_

### Phase 5: Status Notifications (P1)

- [ ] 17. Create notification system
  - Create `web/ui/src/composables/useNotifications.js`
  - Implement toast notification component
  - Support success (green), error (red), warning (yellow) variants
  - Add auto-dismiss after 5 seconds with manual dismiss option
  - Include retry button for error notifications
  - _Requirements: FR-3.2, AC-3_

- [ ]* 18. Write property test for notifications
  - **Property 4: Status Notification Completeness**
  - **Validates: Requirements FR-3.2, AC-3**
  - Test all async operations show loading → success/error states
  - Verify error notifications include retry options
  - _Requirements: FR-3.2_

- [ ] 19. Integrate notifications into workflows
  - Add success notifications for save, generate, publish actions
  - Add error notifications with detailed messages and retry buttons
  - Add warning notifications for validation issues
  - Connect to WebSocket error events
  - _Requirements: FR-3.2, AC-3_

### Phase 6: Manual Mode Support (P1)

- [ ] 20. Implement manual generation mode
  - Add "仅生成骨架" button option in FloatingActionPanel
  - Create separate API calls for outline-only generation
  - Allow editing after outline generation before content generation
  - Add "继续生成全文" button after outline editing
  - _Requirements: FR-1.2, AC-1_

- [ ]* 21. Write property test for manual mode
  - **Property 2: Manual Mode Backward Compatibility**
  - **Validates: Requirements FR-1.2**
  - Test outline-only generation preserves manual edits
  - Verify content generation can be triggered separately
  - _Requirements: FR-1.2_

### Phase 7: Editor Undo/Redo (P1)

- [ ] 22. Implement undo/redo functionality
  - Add history stack management to MarkdownEditor
  - Implement Cmd/Ctrl+Z for undo
  - Implement Cmd/Ctrl+Shift+Z for redo
  - Limit history stack to 50 entries
  - Clear redo stack on new edits
  - _Requirements: FR-4.1_

- [ ] 23. Checkpoint - Verify enhanced features
  - Test all keyboard shortcuts work correctly
  - Verify undo/redo preserves content correctly
  - Test manual mode workflow
  - Ensure all tests pass, ask the user if questions arise.

### Phase 8: List Page Enhancements (P1)

- [ ] 24. Add quick actions to article cards
  - Modify `web/ui/src/views/ArticleListPage.vue`
  - Add "继续生成" button for incomplete articles
  - Display generation progress indicator on cards
  - Add "复制链接" button for published articles
  - Show article step badge on each card
  - _Requirements: FR-5.1, AC-5_

- [ ] 25. Implement filtering and sorting
  - Add filter dropdowns for status (全部/草稿/已发布)
  - Add filter dropdown for step (标题/骨架/内容/已发布)
  - Add sort dropdown (最新更新/创建时间/标题)
  - Implement client-side filtering and sorting logic
  - Persist filter/sort preferences in localStorage
  - _Requirements: FR-5.2, AC-5_

- [ ]* 26. Write property test for list operations
  - **Property 7: Article List Filtering and Sorting**
  - **Validates: Requirements FR-5.1, FR-5.2, FR-5.3, AC-5**
  - Test filtering returns only matching articles for any filter criteria
  - Verify sorting produces consistent results
  - _Requirements: FR-5.2_

### Phase 9: Error Handling & Reliability (P1)

- [ ] 27. Implement WebSocket reconnection logic
  - Create `web/ui/src/composables/useWebSocketReconnect.js`
  - Implement exponential backoff (1s, 2s, 4s, 8s, 16s, max 30s)
  - Display "连接已断开，正在重连..." notification
  - Re-sync article state on successful reconnection
  - _Requirements: NFR-3_

- [ ]* 28. Write property test for WebSocket reconnection
  - **Property 8: WebSocket Reconnection Reliability**
  - **Validates: Requirements NFR-3**
  - Test reconnection attempts use exponential backoff
  - Verify state syncs after reconnection
  - _Requirements: NFR-3_

- [ ] 29. Implement auto-save error handling
  - Add retry logic for failed auto-saves (max 3 attempts)
  - Display error notification after 3 failures
  - Store unsaved content in localStorage as backup
  - Prompt user to manually save after repeated failures
  - _Requirements: FR-4.2, NFR-3_

- [ ]* 30. Write property test for cancellation
  - **Property 9: Generation Cancellation**
  - **Validates: Requirements FR-1.1**
  - Test cancellation preserves partial content for any article
  - Verify article returns to editable state
  - _Requirements: FR-1.1_

### Phase 10: Smart Suggestions (P2)

- [ ] 31. Implement title validation suggestions
  - Add real-time title length validation (10-100 characters)
  - Display warning for titles outside valid range
  - Show character count indicator
  - Provide contextual suggestions
  - _Requirements: FR-4.3_

- [ ] 32. Implement content suggestions
  - Add word count display in editor
  - Show warning when content < 500 words
  - Display "建议继续扩展内容" message
  - Add pre-publish checklist validation
  - _Requirements: FR-4.3_

- [ ]* 33. Write property test for smart suggestions
  - **Property 6: Smart Suggestions Triggering**
  - **Validates: Requirements FR-4.3**
  - Test suggestions appear for invalid title lengths
  - Test suggestions appear for low word counts
  - _Requirements: FR-4.3_

### Phase 11: Batch Operations (P2)

- [ ] 34. Implement batch selection
  - Add checkbox selection to article cards
  - Add "全选" checkbox in list header
  - Track selected articles in component state
  - Show batch action toolbar when articles selected
  - _Requirements: FR-5.3_

- [ ] 35. Implement batch delete
  - Add "批量删除" button in batch toolbar
  - Show confirmation dialog with count
  - Delete selected articles via API
  - Refresh list after deletion
  - _Requirements: FR-5.3, AC-5_

- [ ] 36. Implement batch export
  - Add "批量导出" button in batch toolbar
  - Generate ZIP file with Markdown files
  - Trigger browser download
  - Show progress indicator for large exports
  - _Requirements: FR-5.3_

### Phase 12: Real-time Content Updates (P2)

- [ ] 37. Implement streaming content updates
  - Modify WebSocket handlers to update editor content incrementally
  - Add smooth scroll animation to latest content
  - Implement content diff highlighting for new sections
  - Preserve cursor position during updates
  - _Requirements: FR-3.3_

### Phase 13: Content Update Optimization (P2)

- [ ]* 38. Write property test for content idempotence
  - **Property 10: Content Update Idempotence**
  - **Validates: Requirements FR-4.2**
  - Test saving identical content multiple times only updates timestamp once
  - Verify no unnecessary WebSocket broadcasts
  - _Requirements: FR-4.2_

- [ ] 39. Implement save deduplication
  - Add content hash comparison before saving
  - Skip API call if content unchanged
  - Optimize WebSocket broadcast logic
  - Add debouncing to prevent rapid saves
  - _Requirements: FR-4.2, NFR-1_

### Phase 14: Final Integration & Testing

- [ ] 40. Integration testing
  - Test complete one-click workflow end-to-end
  - Test manual workflow with editing between steps
  - Test error scenarios and recovery
  - Test concurrent editing detection
  - _Requirements: All AC criteria_

- [ ] 41. Performance optimization
  - Verify page load time < 1 second
  - Verify auto-save response < 500ms
  - Verify WebSocket latency < 100ms
  - Optimize bundle size if needed
  - _Requirements: NFR-1_

- [ ] 42. Responsive layout testing
  - Test on mobile viewport (375px, 768px)
  - Verify touch interactions work correctly
  - Adjust FloatingActionPanel for mobile
  - Test keyboard on mobile devices
  - _Requirements: NFR-2_

- [ ] 43. Final checkpoint - Complete system verification
  - Run all unit tests and property tests
  - Verify all acceptance criteria met
  - Test all priority levels (P0, P1, P2)
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties across all inputs
- Unit tests validate specific examples and edge cases
- Implementation follows priority order: P0 (must-have) → P1 (important) → P2 (nice-to-have)
- Backend tasks use Python/FastAPI in `web/api/`
- Frontend tasks use Vue 3 Composition API in `web/ui/src/`
- All WebSocket events maintain backward compatibility with existing system
