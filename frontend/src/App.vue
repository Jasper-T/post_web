<template>
  <div class="app-page postman-shell" :class="{ 'postman-shell-collapsed': sidebarCollapsed }">
    <GroupedCollectionSidebar
      :groups="collectionGroups"
      :active-item-key="editor.name"
      title="Pipelines"
      manager-title="Collections Editor"
      trash-group-name="Deleted"
      trash-label="Deleted"
      @select-item="loadPipeline"
      @create-group="submitCreateGroup"
      @rename-group="submitRenameGroup"
      @delete-group="deleteGroup"
      @move-item="submitMovePipeline"
      @delete-item="handleCollectionDeleteItem"
      @new-item="createAndSaveNewPipeline"
      @clone-item="clonePipelineFromCollection"
      @collapse-change="sidebarCollapsed = $event"
    />

    <section class="workspace-shell">
      <template v-if="hasActivePipeline">
      <div class="request-bar request-bar-top">
        <select v-model="editor.method" class="request-method-select compact-select">
          <option>POST</option>
          <option>GET</option>
          <option>PUT</option>
          <option>PATCH</option>
          <option>DELETE</option>
        </select>
        <div class="meta-input-save-wrap request-url-save-wrap">
          <input v-model.trim="editor.url" class="request-url-input" placeholder="Input API URL" />
          <button
            class="request-url-action-button ui-btn"
            type="button"
            :disabled="savingPipeline"
            title="Create a blank pipeline in Ungrouped"
            aria-label="Create new blank pipeline"
            @click="createAndSaveNewPipeline"
          >
            new
          </button>
          <button
            class="request-url-action-button ui-btn"
            type="button"
            :disabled="savingPipeline || !editor.name"
            title="Clone current pipeline in its group"
            aria-label="Clone current pipeline"
            @click="cloneCurrentPipeline"
          >
            clone
          </button>
          <button
            class="ui-icon-save meta-save-button ui-btn ui-icon-btn"
            type="button"
            :disabled="savingPipeline"
            title="Save pipeline URL"
            aria-label="Save pipeline URL"
            @click="savePipeline"
          >
            <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M5 4h12l2 2v14H5z" />
              <path d="M8 4v6h8V4M8 20v-6h8v6" />
            </svg>
          </button>
        </div>
      </div>

      <div class="request-meta-bar request-meta-bar-compact">
        <label class="inline-meta-field">
          <span>Pipeline Name</span>
          <div class="meta-input-save-wrap">
            <input v-model.trim="editor.name" placeholder="demo_detection_v2" />
            <button
              class="ui-icon-save meta-save-button ui-btn ui-icon-btn"
              type="button"
              :disabled="savingPipeline"
              title="Save pipeline name"
              aria-label="Save pipeline name"
              @click="savePipeline"
            >
              <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 4h12l2 2v14H5z" />
                <path d="M8 4v6h8V4M8 20v-6h8v6" />
              </svg>
            </button>
          </div>
        </label>
        <label class="inline-meta-field">
          <span>Display Name</span>
          <div class="meta-input-save-wrap">
            <input v-model.trim="editor.displayName" placeholder="Demo Detection V2" />
            <button
              class="ui-icon-save meta-save-button ui-btn ui-icon-btn"
              type="button"
              :disabled="savingPipeline"
              title="Save display name"
              aria-label="Save display name"
              @click="savePipeline"
            >
              <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 4h12l2 2v14H5z" />
                <path d="M8 4v6h8V4M8 20v-6h8v6" />
              </svg>
            </button>
          </div>
        </label>
        <label class="inline-meta-field grow">
          <span>Image Path</span>
          <div class="path-picker-row">
            <div class="meta-input-save-wrap">
              <input v-model="editor.inputPath" placeholder="Select image or directory" @change="loadResponseQueue(editor.inputPath)" />
              <button
                class="ui-icon-save meta-save-button ui-btn ui-icon-btn"
                type="button"
                :disabled="queueLoading || !editor.inputPath"
                title="Load image list"
                aria-label="Load image list"
                @click="loadResponseQueue(editor.inputPath)"
              >
                <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M5 4h12l2 2v14H5z" />
                  <path d="M8 4v6h8V4M8 20v-6h8v6" />
                </svg>
              </button>
            </div>
            <button class="ui-btn" type="button" @click="openFileBrowser">Browse</button>
          </div>
        </label>
      </div>

      <div class="workspace-view-shell">
        <div class="workspace-view-switch" role="tablist" aria-label="Workspace View">
          <button
            class="workspace-view-button"
            :class="{ active: activeWorkspaceView === 'request' }"
            type="button"
            role="tab"
            :aria-selected="activeWorkspaceView === 'request'"
            @click="activeWorkspaceView = 'request'"
          >
            Request
          </button>
          <button
            class="workspace-view-button"
            :class="{ active: activeWorkspaceView === 'response' }"
            type="button"
            role="tab"
            :aria-selected="activeWorkspaceView === 'response'"
            @click="activeWorkspaceView = 'response'"
          >
            Response
          </button>
        </div>

        <section v-if="activeWorkspaceView === 'request'" class="panel request-panel workspace-view-panel">
          <div class="editor-tabs">
            <button
              v-for="tab in requestTabs"
              :key="tab.id"
              class="editor-tab"
              :class="{ active: activeRequestTab === tab.id }"
              type="button"
              :disabled="tab.disabled"
              :title="tab.disabled ? tab.disabledReason : ''"
              @click="switchRequestTab(tab)"
            >
              {{ tab.label }}
            </button>
          </div>

          <div class="request-tab-body">
            <div v-if="formError" class="tool-alert error">{{ formError }}</div>
            <div v-if="formSuccess" class="tool-alert success">{{ formSuccess }}</div>

            <JsonFieldBuilder
              v-if="activeRequestTab === 'header'"
              title="Header JSON"
              v-model="headerTemplate"
              :can-preview="Boolean(savedAssetTexts.header)"
              :saved-text="savedAssetTexts.header"
              :saving="assetSavingKey === 'header'"
              @save="saveJsonAsset('header', $event)"
            />

            <JsonFieldBuilder
              v-else-if="activeRequestTab === 'body'"
              title="Body JSON"
              v-model="bodyTemplate"
              :can-preview="Boolean(savedAssetTexts.body)"
              :saved-text="savedAssetTexts.body"
              :saving="assetSavingKey === 'body'"
              @save="saveJsonAsset('body', $event)"
            />

            <JsonFieldBuilder
              v-else-if="activeRequestTab === 'response'"
              title="Response JSON"
              v-model="responseTemplate"
              :can-preview="Boolean(savedAssetTexts.response)"
              :saved-text="savedAssetTexts.response"
              :saving="assetSavingKey === 'response'"
              @save="saveJsonAsset('response', $event)"
            />

            <ResponseMappingEditor
              v-else-if="activeRequestTab === 'mapping'"
              :model-value="mappingModel"
              :source-path-options="responseMappingPathOptions.fieldPaths"
              :collection-path-options="responseMappingPathOptions.collectionPaths"
              :item-path-options="responseMappingPathOptions.itemPaths"
              @update:model-value="mappingModel = $event"
              @save="saveMappingAsset"
            />

            <PostConfigEditor
              v-else-if="activeRequestTab === 'post-config'"
              :model-value="postConfigModel"
              :body-path-options="bodyFieldPathOptions"
              @update:model-value="postConfigModel = $event"
              @save="savePostConfigAsset"
            />

            <div v-else class="empty-state compact-empty-state">
              Import or save Body JSON and Response JSON first.
            </div>
          </div>
        </section>

        <section v-else class="panel response-panel workspace-view-panel">
          <div class="response-display-grid" :style="responseGridStyle">
            <section class="response-detail-panel">
              <div class="editor-tabs response-tabs">
                <button
                  v-for="tab in responseTabs"
                  :key="tab.id"
                  class="editor-tab"
                  :class="{ active: activeResponseTab === tab.id }"
                  type="button"
                  @click="activeResponseTab = tab.id"
                >
                  {{ tab.label }}
                </button>
              </div>

              <div class="response-body">
                <div v-if="runError" class="tool-alert error">{{ runError }}</div>
                <template v-if="activeResponseTab === 'response-result'">
                  <div class="response-result-panel">
                    <div class="response-result-toolbar">
                      <div class="preview-mode-switch ui-segmented" role="group" aria-label="Response result view">
                        <button type="button" :class="{ active: responseResultView === 'parsed' }" @click="responseResultView = 'parsed'">Parsed</button>
                        <button type="button" :class="{ active: responseResultView === 'raw' }" @click="responseResultView = 'raw'">Raw</button>
                      </div>
                    </div>
                    <div v-if="responseResultView === 'raw' && hasResponseValue(selectedResult, 'rawResponse')" class="result-json-block">
                      <pre>{{ stringify(selectedResult.rawResponse) }}</pre>
                    </div>
                    <div v-else-if="responseResultView === 'parsed' && hasResponseValue(selectedResult, 'parsed')" class="result-json-block">
                      <pre>{{ stringify(normalizedParsedResult) }}</pre>
                    </div>
                    <div v-else-if="selectedResult?.error" class="tool-alert error">{{ selectedResult.error }}</div>
                    <div v-else class="empty-state compact-empty-state">Select an image with a completed result.</div>
                  </div>
                </template>

                <template v-else-if="activeResponseTab === 'image-preview'">
                  <div v-if="selectedImagePath" class="response-image-preview">
                    <div class="response-image-preview-header">
                      <div class="preview-title-block"><strong :title="selectedImagePath">{{ baseName(selectedImagePath) }}</strong><small v-if="previewMode === 'gt' && selectedResult?.gtError">{{ selectedResult.gtError }}</small></div>
                      <div class="preview-toolbar-actions">
                        <button
                          class="ui-action-refresh ui-icon-refresh preview-refresh-button ui-btn ui-icon-btn"
                          :class="{ refreshing: isRefreshingCurrentVisualization }"
                          type="button"
                          :title="previewMode === 'pred' ? 'Refresh Pred annotations' : 'Refresh GT annotations'"
                          :aria-label="previewMode === 'pred' ? 'Refresh Pred annotations' : 'Refresh GT annotations'"
                          :disabled="!canRefreshCurrentVisualization"
                          @click="refreshCurrentVisualization"
                        >
                          <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M17.7 6.3A8 8 0 1 0 20 12h-2a6 6 0 1 1-1.76-4.24L13 11h8V3l-3.3 3.3Z" />
                          </svg>
                        </button>
                        <button
                          class="ui-icon-download preview-download-button ui-btn ui-icon-btn"
                          type="button"
                          title="Download annotation folder"
                          aria-label="Download annotation folder"
                          :disabled="!canDownloadVisualizations || visualizationDownloading"
                          @click="downloadVisualizationFolder"
                        >
                          <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M12 3v12" />
                            <path d="m7 10 5 5 5-5" />
                            <path d="M5 21h14" />
                          </svg>
                        </button>
                        <div class="preview-mode-switch ui-segmented" role="group" aria-label="Pred GT view">
                          <button type="button" :class="{ active: previewMode === 'pred' }" @click="previewMode = 'pred'">Pred</button>
                          <button type="button" :class="{ active: previewMode === 'gt' }" @click="previewMode = 'gt'">GT</button>
                        </div>
                      </div>
                    </div>
                    <div
                      ref="previewStageRef"
                      class="response-image-preview-stage"
                      tabindex="0"
                      role="region"
                      aria-label="Image preview. Use left and right arrow keys to switch images."
                      @mousedown="focusPreviewNavigation"
                      @keydown.left.prevent="selectPreviewByOffset(-1)"
                      @keydown.right.prevent="selectPreviewByOffset(1)"
                    >
                      <div v-if="(gtGenerating || gtRefreshing) && previewMode === 'gt'" class="preview-status-message">Generating GT annotation preview...</div>
                      <template v-else-if="currentPreviewPath">
                        <img :src="imageContentUrl(currentPreviewPath)" :alt="baseName(selectedImagePath)" />
                      </template>
                      <div v-else class="preview-status-message">Current image is not available.</div>
                    </div>
                  </div>
                  <div v-else class="empty-state compact-empty-state">Select an image to preview.</div>
                </template>
                <template v-else-if="activeResponseTab === 'result-evaluation'">
                  <div class="evaluation-panel">
                    <div class="evaluation-toolbar">
                      <label class="evaluation-threshold-field">
                        <span>Conf</span>
                        <input v-model.number="evaluationConfThreshold" type="number" min="0" max="1" step="0.01" />
                      </label>
                      <label class="evaluation-threshold-field">
                        <span>IoU</span>
                        <input v-model.number="evaluationIouThreshold" type="number" min="0" max="1" step="0.01" />
                      </label>
                      <button class="ui-btn ui-btn-primary" type="button" :disabled="!evaluationCanRun || evaluationRunning" @click="runResultEvaluation">
                        {{ evaluationRunning ? 'Evaluating...' : 'Run Evaluation' }}
                      </button>
                    </div>

                    <div class="response-queue-summary evaluation-summary-line">
                      <span>{{ evaluationPredictions.length }} images with parsed predictions</span>
                      <span>{{ evaluationImageDir || '-' }}</span>
                    </div>

                    <div class="names-summary-panel">
                      <strong>Names</strong>
                      <span>{{ namesSummary }}</span>
                      <button class="ui-btn" type="button" @click="openGTSettingsDialog">Settings</button>
                    </div>

                    <div v-if="evaluationError" class="tool-alert error">{{ evaluationError }}</div>
                    <div v-else-if="!evaluationCanRun" class="empty-state compact-empty-state">Run images first, then set GT label folder and names in Settings.</div>

                    <section class="evaluation-section">
                      <div class="evaluation-section-title">
                        <strong>Predictions</strong>
                        <span>parsed response, realtime</span>
                      </div>
                      <div class="evaluation-metrics-grid">
                        <div class="evaluation-metric"><span>Images</span><strong>{{ predictionStats.images }}</strong></div>
                        <div class="evaluation-metric"><span>Instances</span><strong>{{ predictionStats.instances }}</strong></div>
                        <div class="evaluation-metric"><span>Names</span><strong>{{ gtNames.length }}</strong></div>
                      </div>
                    </section>

                    <template v-if="evaluationResult?.metrics">
                      <section class="evaluation-section">
                        <div class="evaluation-section-title">
                          <strong>Ground Truth</strong>
                          <span>dsetkit.dataset</span>
                        </div>
                        <div class="evaluation-metrics-grid">
                          <div class="evaluation-metric"><span>Images</span><strong>{{ evaluationResult.dataset?.images ?? 0 }}</strong></div>
                          <div class="evaluation-metric"><span>Background</span><strong>{{ evaluationResult.dataset?.backgrounds ?? 0 }}</strong></div>
                          <div class="evaluation-metric"><span>Instances</span><strong>{{ evaluationResult.dataset?.instances ?? 0 }}</strong></div>
                          <div class="evaluation-metric"><span>Names</span><strong>{{ gtNames.length }}</strong></div>
                        </div>
                      </section>

                      <section class="evaluation-section">
                        <div class="evaluation-section-title">
                          <strong>Evaluation Result</strong>
                          <span>dsetkit.evaluator</span>
                        </div>
                        <div class="evaluation-metrics-grid">
                          <div class="evaluation-metric"><span>Images</span><strong>{{ evaluationResult.metrics.images ?? evaluationResult.evaluatedImages }}</strong></div>
                          <div class="evaluation-metric"><span>Instances</span><strong>{{ evaluationResult.metrics.instances ?? 0 }}</strong></div>
                          <div class="evaluation-metric"><span>Precision</span><strong>{{ formatMetric(evaluationResult.metrics.precision) }}</strong></div>
                          <div class="evaluation-metric"><span>Recall</span><strong>{{ formatMetric(evaluationResult.metrics.recall) }}</strong></div>
                          <div class="evaluation-metric"><span>F1</span><strong>{{ formatMetric(evaluationResult.metrics.f1) }}</strong></div>
                          <div class="evaluation-metric"><span>{{ evaluationApKey }}</span><strong>{{ formatMetric(evaluationResult.metrics[evaluationApKey] ?? evaluationResult.metrics.mAP) }}</strong></div>
                          <div class="evaluation-metric"><span>{{ evaluationApRangeKey }}</span><strong>{{ formatMetric(evaluationResult.metrics[evaluationApRangeKey]) }}</strong></div>
                        </div>

                        <div class="evaluation-table-shell ui-table">
                          <table class="evaluation-table">
                            <thead>
                              <tr>
                                <th>Class</th>
                                <th>Images</th>
                                <th>Instances</th>
                                <th>Precision</th>
                                <th>Recall</th>
                                <th>{{ evaluationApKey }}</th>
                                <th>{{ evaluationApRangeKey }}</th>
                                <th>F1</th>
                                <th>TP</th>
                                <th>FP</th>
                                <th>FN</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr v-for="row in evaluationClassRows" :key="row.name">
                                <td>{{ row.name }}</td>
                                <td>{{ row.images ?? 0 }}</td>
                                <td>{{ row.instances ?? 0 }}</td>
                                <td>{{ formatMetric(row.precision) }}</td>
                                <td>{{ formatMetric(row.recall) }}</td>
                                <td>{{ formatMetric(row[evaluationApKey] ?? row.ap) }}</td>
                                <td>{{ formatMetric(row[evaluationApRangeKey] ?? row.ap_range) }}</td>
                                <td>{{ formatMetric(row.f1) }}</td>
                                <td>{{ row.tp ?? 0 }}</td>
                                <td>{{ row.fp ?? 0 }}</td>
                                <td>{{ row.fn ?? 0 }}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </section>
                    </template>
                  </div>
                </template>

                <template v-else-if="activeResponseTab === 'annotation-conversion'">
                  <div class="annotation-conversion-panel">
                    <div class="conversion-toolbar">
                      <div class="preview-mode-switch ui-segmented" role="group" aria-label="Annotation conversion source">
                        <button type="button" :class="{ active: conversionMode === 'pred' }" @click="conversionMode = 'pred'">Pred</button>
                        <button type="button" :class="{ active: conversionMode === 'gt' }" @click="conversionMode = 'gt'">GT</button>
                      </div>
                      <label class="evaluation-threshold-field">
                        <span>Target</span>
                        <select v-model="conversionTargetFormat" class="compact-select">
                          <option value="labelme">LabelMe</option>
                          <option value="voc">VOC</option>
                          <option value="yolo">YOLO</option>
                        </select>
                      </label>
                      <button class="ui-btn ui-btn-primary" type="button" :disabled="!conversionCanRun || conversionRunning" @click="runAnnotationConversion">
                        {{ conversionRunning ? 'Converting...' : 'Convert' }}
                      </button>
                    </div>

                    <div class="names-summary-panel">
                      <strong>Names</strong>
                      <span>{{ namesSummary }}</span>
                      <button class="ui-btn" type="button" @click="openGTSettingsDialog">Settings</button>
                    </div>
                    <div class="names-summary-panel">
                      <strong>New Annos</strong>
                      <span>{{ currentConversionCachePath }}</span>
                    </div>

                    <div class="response-queue-summary evaluation-summary-line">
                      <span v-if="conversionMode === 'pred'">{{ conversionPredictions.length }} Pred images will be converted</span>
                      <span v-else>GT folder: {{ gtLabelDir || '-' }}</span>
                      <span>Target {{ conversionTargetFormat }}</span>
                    </div>

                    <div v-if="conversionError" class="tool-alert error">{{ conversionError }}</div>
                    <div v-if="conversionResult" class="tool-alert success">
                      <strong>{{ conversionResult.message }}</strong>
                      <span v-if="conversionResult.outputDir">New Annos{{ conversionResult.outputDir }}</span>
                    </div>
                    <div v-else-if="!conversionCanRun" class="empty-state compact-empty-state">Set names in Settings, then choose Pred results or a GT label folder to convert.</div>

                    <div v-if="conversionMode === 'pred' && selectedResult?.parsed" class="result-json-block annotation-conversion-preview">
                      <pre>{{ stringify(normalizedParsedResult) }}</pre>
                    </div>
                  </div>
                </template>
              </div>
            </section>

            <div
              class="response-column-divider"
              role="separator"
              aria-orientation="vertical"
              title="Drag to resize panels"
              @mousedown="startResponseResize"
            ></div>

            <aside class="response-queue-panel">
              <div class="response-queue-toolbar">
                <label class="response-select-all" title="Select all images in the current filtered view">
                  <input
                    :key="`select-all-${responseStatusFilter}`"
                    type="checkbox"
                    aria-label="Select all images in the current view"
                    :checked="filteredSelectAllChecked"
                    :indeterminate="filteredSelectAllIndeterminate"
                    :disabled="!filteredResponseQueue.length"
                    @change="toggleFilteredSelection($event.target.checked)"
                  />
                  <span>Select all</span>
                </label>
                <button
                  class="ui-icon-settings response-settings-button ui-btn ui-icon-btn"
                  type="button"
                  title="Preview settings"
                  aria-label="Preview settings"
                  @click="openGTSettingsDialog"
                >
                  <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5Z" />
                    <path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.04.04a2 2 0 0 1-2.83 2.83l-.04-.04A1.8 1.8 0 0 0 15 19.45a1.8 1.8 0 0 0-1 .55V20a2 2 0 0 1-4 0v-.06a1.8 1.8 0 0 0-1-.55 1.8 1.8 0 0 0-1.98.36l-.04.04a2 2 0 0 1-2.83-2.83l.04-.04A1.8 1.8 0 0 0 4.55 15a1.8 1.8 0 0 0-.55-1H4a2 2 0 0 1 0-4h.06a1.8 1.8 0 0 0 .55-1 1.8 1.8 0 0 0-.36-1.98l-.04-.04a2 2 0 0 1 2.83-2.83l.04.04A1.8 1.8 0 0 0 9 4.55a1.8 1.8 0 0 0 1-.55V4a2 2 0 0 1 4 0v.06a1.8 1.8 0 0 0 1 .55 1.8 1.8 0 0 0 1.98-.36l.04-.04a2 2 0 0 1 2.83 2.83l-.04.04A1.8 1.8 0 0 0 19.45 9c.2.35.38.67.55 1H20a2 2 0 0 1 0 4h-.06a1.8 1.8 0 0 0-.54 1Z" />
                  </svg>
                </button>
                <select v-model="responseStatusFilter" class="response-status-filter compact-select" aria-label="Filter response status">
                  <option value="all">All</option>
                  <option value="new">New</option>
                  <option value="success">Success</option>
                  <option value="failed">Failed</option>
                  <option value="abort">Abort</option>
                </select>
                <button
                  class="response-send-all ui-btn ui-btn-primary"
                  :class="{ 'is-running': runningAll }"
                  type="button"
                  :title="runningAll ? 'Abort sending' : `Send all selected (${selectedResponseCount})`"
                  :aria-label="runningAll ? 'Abort sending' : `Send all selected (${selectedResponseCount})`"
                  :disabled="!runningAll && (!editor.name || !editor.inputPath || !selectedResponseCount)"
                  @click="runningAll ? abortAllImages() : runAllImages()"
                >
                  <svg v-if="runningAll" class="button-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M7 7h10v10H7V7Z" />
                  </svg>
                  <svg v-else class="button-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M8 5v14l11-7L8 5Z" />
                  </svg>
                  <span>{{ runningAll ? "Abort" : `Send All (${selectedResponseCount})` }}</span>
                </button>
              </div>

              <div class="response-queue-summary">
                <span>{{ filteredResponseQueue.length }} / {{ responseQueue.length }} images</span>
                <span>new {{ responseStatusCounts.new }} / success {{ responseStatusCounts.success }} / failed {{ responseStatusCounts.failed }} / abort {{ responseStatusCounts.abort }}</span>
              </div>

              <div v-if="queueLoading" class="empty-state compact-empty-state">Loading images...</div>
              <div v-else-if="!responseQueue.length" class="empty-state compact-empty-state">Select an image or folder first.</div>
              <div v-else ref="responseListShellRef" class="response-list-shell">
                <div
                  v-for="item in filteredResponseQueue"
                  :key="item.imagePath"
                  class="response-list-item ui-list-item"
                  :data-response-image-path="item.imagePath"
                  :class="[item.status, { active: selectedImagePath === item.imagePath }]"
                  role="button"
                  tabindex="0"
                  @click="selectedImagePath = item.imagePath"
                  @keydown.enter="selectedImagePath = item.imagePath"
                >
                  <div class="response-list-item-main">
                    <label class="response-row-check" :title="'Select ' + item.name" @click.stop>
                      <input
                        type="checkbox"
                        :checked="item.selected"
                        @change="setResponseSelected(item.imagePath, $event.target.checked)"
                      />
                    </label>
                    <strong :title="item.imagePath">{{ item.name }}</strong>
                    <span class="response-status-badge">{{ item.status }}</span>
                  </div>
                  <div class="response-list-item-meta">
                    <small>{{ item.elapsedMs == null ? "-" : item.elapsedMs + " ms" }}</small><small v-if="item.gtError" class="response-row-warning">{{ item.gtError }}</small>
                    <button
                      class="response-item-send"
                      type="button"
                      :disabled="runningAll || item.sending || !editor.name"
                      :title="'Send ' + item.name"
                      :aria-label="'Send ' + item.name"
                      @click.stop="runSingleImage(item)"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="m4 4 17 8-17 8 3-8z" />
                        <path d="M7 12h14" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </aside>
          </div>
        </section>
      </div>
      </template>

      <div v-else class="empty-pipeline-page">
        <div class="empty-pipeline-card">
          <p class="eyebrow">Pipeline</p>
          <h2>Welcome !</h2>
          <p>Choose pipeline in Collections</p>
          <button
            class="ui-btn ui-btn-primary"
            type="button"
            :disabled="savingPipeline"
            @click="createAndSaveNewPipeline"
          >
            New pipeline
          </button>
        </div>
      </div>
    </section>

    <div v-if="showFileBrowser" class="file-browser-backdrop" @click.self="closeFileBrowser">
      <div class="file-browser-dialog file-browser-dialog-single-panel" :data-upload-parent-path="uploadParentPath">
        <FileSystemTree
          :root-node="rootNode"
          :selected-path="activePath"
          :highlight-path="uploadSelectionPath"
          :title="`Data Root (${appConfig.filesystemRoot})`"
          eyebrow="File System"
          loading-message="Loading..."
          :filter-loader="fetchFilteredChildren"
          show-upload-button
          :upload-target-path="appConfig.datasetsRoot"
          @upload-complete="handleUploadComplete"
          @refresh="reloadRoot"
          @select="selectPath"
          @highlight="selectUploadParent"
          @toggle="toggleNode"
          @load-more="loadMoreChildren"
        >
          <template #header-actions>
            <button
              class="ui-action-close ui-icon-close file-browser-close-button ui-btn ui-icon-btn"
              type="button"
              title="Close"
              aria-label="Close"
              @click="closeFileBrowser"
            >
              <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6l12 12M18 6 6 18" />
              </svg>
            </button>
          </template>
        </FileSystemTree>
      </div>
    </div>

    <div v-if="resultsBrowser.visible" class="file-browser-backdrop" @click.self="closeResultsBrowser">
      <div class="file-browser-dialog file-browser-dialog-panel-with-footer">
        <FileSystemTree
          :root-node="resultsRootNode"
          :selected-path="resultsBrowser.selectedPath"
          eyebrow=""
          title="Run Results"
          loading-message="Loading..."
          :filter-loader="fetchFilteredChildren"
          @refresh="reloadResultsRoot"
          @select="selectResultsPath"
          @toggle="toggleNode"
          @load-more="loadMoreChildren"
        >
          <template #header-actions>
            <button class="ui-action-close ui-icon-close file-browser-close-button ui-btn ui-icon-btn" type="button" title="Close" aria-label="Close results browser" @click="closeResultsBrowser"><svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg></button>
          </template>
        </FileSystemTree>

        <div class="file-browser-dialog-footer">
          <div class="file-browser-path-preview">
            <span>Selected</span>
            <strong>{{ resultsBrowser.selectedPath || "Not selected" }}</strong>
          </div>
          <button
            class="ui-btn ui-btn-primary"
            type="button"
            :disabled="!resultsBrowser.selectedPath"
            @click="loadSelectedResultsFolder"
          >
            Load
          </button>
        </div>
      </div>
    </div>

    <div v-if="gtBrowser.visible" class="file-browser-backdrop" @click.self="closeGTBrowser">
      <div class="file-browser-dialog file-browser-dialog-panel-with-footer">
        <FileSystemTree
          :root-node="gtRootNode"
          :selected-path="gtBrowser.selectedPath"
          :title="`Data Root (${appConfig.filesystemRoot})`"
          eyebrow="GT Labels"
          loading-message="Loading..."
          :filter-loader="fetchFilteredChildren"
          @refresh="reloadGTRoot"
          @select="selectGTLabelFolder"
          @highlight="highlightGTPath"
          @toggle="toggleNode"
          @load-more="loadMoreChildren"
        >
          <template #header-actions>
            <button class="ui-action-close ui-icon-close file-browser-close-button ui-btn ui-icon-btn" type="button" title="Close" aria-label="Close GT browser" @click="closeGTBrowser"><svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg></button>
          </template>
        </FileSystemTree>
        <div class="file-browser-dialog-footer">
          <div class="file-browser-path-preview"><span>Double-click a folder to confirm</span><strong>{{ gtBrowser.selectedPath || 'Not selected' }}</strong></div>
        </div>
      </div>
    </div>
<div v-if="gtSettingsDialog.visible" class="json-import-backdrop" @click.self="closeGTSettingsDialog">
      <div class="json-import-dialog gt-settings-dialog">
        <div class="json-import-dialog-header">
          <h4>Settings</h4>
          <button class="ui-action-close ui-icon-close ui-btn ui-icon-btn" type="button" title="Close" aria-label="Close GT settings" @click="closeGTSettingsDialog"><svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg></button>
        </div>
        <div class="gt-settings-body">
          <section class="gt-settings-section cache-settings-section">
            <div class="gt-settings-section-header">
              <strong>Cache dir</strong>
              <span>{{ currentCachePath }}</span>
            </div>
          </section>
          <section class="cache-list-section">
            <div class="cache-list-header">
              <strong>Cache Folders</strong>
              <button class="ui-action-refresh ui-icon-refresh ui-btn ui-icon-btn" type="button" :disabled="!editor.name || cacheLoading" title="Refresh" aria-label="Refresh cache" @click="loadPipelineCache"></button>
            </div>
            <div v-if="cacheError" class="tool-alert error">{{ cacheError }}</div>
            <div class="cache-folder-list">
              <label v-for="item in cacheItems" :key="item.name" class="cache-folder-row ui-list-item">
                <input type="checkbox" :checked="selectedCacheBuckets.includes(item.name)" @change="toggleCacheBucket(item.name, $event.target.checked)" />
                <span :title="item.path">{{ item.name }}</span>
                <small>{{ (item.children || []).join(', ') || '-' }}</small>
              </label>
              <div v-if="!cacheLoading && !cacheItems.length" class="empty-state compact-empty-state">No cache folders.</div>
              <div v-if="cacheLoading" class="empty-state compact-empty-state">Loading cache...</div>
            </div>
            <div class="cache-list-actions">
              <label class="cache-select-all"><input type="checkbox" :checked="cacheAllSelected" :disabled="!cacheItems.length" @change="toggleAllCacheBuckets($event.target.checked)" /> Select all</label>
              <button class="ui-action-delete ui-action-delete-all ui-icon-delete cache-delete-button ui-btn ui-btn-danger" type="button" :disabled="!selectedCacheBuckets.length" @click="deleteSelectedCacheBuckets">
                <span class="ui-action-label">Delete All</span>
              </button>
            </div>
          </section>
          <label class="tool-field">
            <span>Format</span>
            <select v-model="gtSettingsDraft.format" class="compact-select">
              <option value="yolo">YOLO</option>
              <option value="labelme">LabelMe</option>
              <option value="voc">VOC</option>
            </select>
          </label>
          <label class="tool-field">
            <span>Label Folder</span>
            <div class="gt-settings-folder-row">
              <input v-model="gtSettingsDraft.labelDir" type="text" placeholder="Select label folder" readonly />
              <button class="ui-btn" type="button" @click="openGTBrowser">Browse</button>
            </div>
          </label>
          <label class="tool-field">
            <span>Names</span>
            <textarea v-model="gtSettingsDraft.names" class="gt-names-textarea" placeholder="person&#10;car&#10;bicycle"></textarea>
          </label>
        </div>
        <div class="json-import-dialog-footer">
          <button class="ui-btn" type="button" @click="closeGTSettingsDialog">Cancel</button>
          <button class="ui-btn ui-btn-primary" type="button" :disabled="gtGenerating || gtRefreshing" @click="applyGTSettings">Apply</button>
        </div>
      </div>
    </div>

    <div v-if="assetReader.visible" class="file-browser-backdrop" @click.self="closeAssetReader">
      <div class="file-browser-dialog file-browser-dialog-panel-with-footer">
        <FileSystemTree
          :root-node="rootNode"
          :selected-path="assetReader.selectedPath"
          :title="`Read ${assetReader.kind === 'mapping' ? 'Parsing' : 'Request Config'} JSON`"
          eyebrow="Project Root"
          loading-message="Loading..."
          :filter-loader="fetchJsonOnlyChildren"
          @refresh="reloadRoot"
          @select="selectAssetPath"
          @toggle="toggleNode"
          @load-more="loadMoreChildren"
        >
          <template #header-actions>
            <button class="ui-action-close ui-icon-close file-browser-close-button ui-btn ui-icon-btn" type="button" title="Close" aria-label="Close asset reader" @click="closeAssetReader"><svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg></button>
          </template>
        </FileSystemTree>

        <div class="file-browser-dialog-footer">
          <div class="file-browser-path-preview">
            <span>Selected</span>
            <strong>{{ assetReader.selectedPath || "None" }}</strong>
          </div>
          <button class="ui-btn ui-btn-primary" type="button" :disabled="!assetReader.selectedPath" @click="readSelectedAsset">
            Load
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
import FileSystemTree from "./components/FileSystemTree.vue";
import GroupedCollectionSidebar from "./components/GroupedCollectionSidebar.vue";
import JsonFieldBuilder from "./components/JsonFieldBuilder.vue";
import PostConfigEditor from "./components/PostConfigEditor.vue";
import ResponseMappingEditor from "./components/ResponseMappingEditor.vue";

const directoryPageSize = 20;
const ungroupedLabel = "Ungrouped";
const deletedGroupLabel = "Deleted";

const baseRequestTabs = [
  { id: "header", label: "Header" },
  { id: "body", label: "Body" },
  { id: "response", label: "Response" },
  { id: "mapping", label: "Parsing" },
  { id: "post-config", label: "Request Config" },
];

const responseTabs = [
  { id: "response-result", label: "Response Result" },
  { id: "image-preview", label: "Image Preview" },
  { id: "result-evaluation", label: "Result Evaluation" },
  { id: "annotation-conversion", label: "Annotation Conversion" },
];

const activeRequestTab = ref("header");
const activeResponseTab = ref("response-result");
const responseResultView = ref("parsed");
const previewMode = ref("pred");
const gtFormat = ref("yolo");
const gtLabelDir = ref("");
const gtNames = ref([]);
const gtSettingsDialog = reactive({ visible: false });
const gtSettingsDraft = reactive({ labelDir: "", format: "yolo", names: "" });
const gtGenerating = ref(false);
const predRefreshing = ref(false);
const gtRefreshing = ref(false);
const visualizationRefreshNonce = ref(0);
const evaluationRunning = ref(false);
const evaluationError = ref("");
const evaluationResult = ref(null);
const conversionMode = ref("pred");
const conversionTargetFormat = ref("yolo");
const conversionOutDir = ref("");
const conversionRunning = ref(false);
const conversionError = ref("");
const conversionResult = ref(null);
const cacheItems = ref([]);
const selectedCacheBuckets = ref([]);
const cacheLoading = ref(false);
const cacheError = ref("");
const evaluationConfThreshold = ref(0.5);
const evaluationIouThreshold = ref(0.5);
const visualizationDownloading = ref(false);
const visualizationDownloadError = ref("");
const selectedImagePath = ref("");
const previewStageRef = ref(null);
const responseListShellRef = ref(null);
const responseStatusFilter = ref("all");
const responseQueue = ref([]);
const queueLoading = ref(false);
const runningAll = ref(false);
const abortAllRequested = ref(false);
const activeBatchController = ref(null);
const responseLeftPercent = ref(64);
const activePath = ref("");
const uploadSelectionPath = ref("");
const appConfig = reactive({ filesystemRoot: "", datasetsRoot: "", frontendDist: "" });
const uploadParentPath = ref("");
const showFileBrowser = ref(false);
const sidebarCollapsed = ref(false);
const activeWorkspaceView = ref("request");
const pipelineItems = ref([]);
const pipelineGroups = ref([]);
const assetSavingKey = ref("");
const savingPipeline = ref(false);
const persistedPipelineName = ref("");
const formError = ref("");
const formSuccess = ref("");
const runError = ref("");
const runResult = ref(null);
const headerTemplate = ref({});
const bodyTemplate = ref({});
const responseTemplate = ref({});
const mappingModel = ref(createDefaultMappingModel());
const postConfigModel = ref(createDefaultPostConfig());
const savedAssetTexts = reactive({
  header: "",
  body: "",
  response: "",
  mapping: "",
  post_config: "",
});

const assetReader = reactive({
  visible: false,
  kind: "mapping",
  selectedPath: "",
});

const resultsBrowser = reactive({
  visible: false,
  selectedPath: "",
});

const resultsRootNode = ref(null);
const gtRootNode = ref(null);

const gtBrowser = reactive({ visible: false, selectedPath: "" });

const editor = reactive(createEmptyEditor());
const hasActivePipeline = computed(() => Boolean(persistedPipelineName.value || editor.name));

const rootNode = ref(createRootNode("", "Data Root"));

const selectedResult = computed(() =>
  responseQueue.value.find((item) => item.imagePath === selectedImagePath.value) || null,
);

const currentVisualizationPath = computed(() => {
  const item = selectedResult.value;
  if (!item) return "";
  return previewMode.value === "pred"
    ? item.predCachePath || item.predSavedPath || ""
    : item.gtCachePath || item.gtSavedPath || "";
});

const currentPreviewPath = computed(() => currentVisualizationPath.value || selectedImagePath.value || "");

const downloadableVisualizationItems = computed(() => {
  const cacheKey = previewMode.value === "pred" ? "predCachePath" : "gtCachePath";
  const savedKey = previewMode.value === "pred" ? "predSavedPath" : "gtSavedPath";
  return responseQueue.value
    .filter((item) => item[cacheKey] || item[savedKey])
    .map((item) => ({ ...item, downloadPath: item[cacheKey] || item[savedKey] }));
});

const canDownloadVisualizations = computed(() => downloadableVisualizationItems.value.length > 0);

const isRefreshingCurrentVisualization = computed(() =>
  previewMode.value === "pred" ? predRefreshing.value : gtGenerating.value || gtRefreshing.value,
);

const canRefreshCurrentVisualization = computed(() => {
  const item = selectedResult.value;
  if (!editor.name || !item?.imagePath) return false;
  if (previewMode.value === "pred") return Boolean(item.parsed) && !predRefreshing.value;
  return Boolean(gtLabelDir.value && gtNames.value.length) && !gtGenerating.value && !gtRefreshing.value;
});

const gtPreviewMessage = computed(() => {
  if (!gtNames.value.length) return "Please configure GT names first.";
  if (!gtLabelDir.value) return "Please select a GT label folder.";
  return selectedResult.value?.gtError || "No matching GT annotation found for this image.";
});

const filteredResponseQueue = computed(() =>
  responseStatusFilter.value === "all"
    ? responseQueue.value
    : responseQueue.value.filter((item) => item.status === responseStatusFilter.value),
);

const selectedResponseCount = computed(() => responseQueue.value.filter((item) => item.selected).length);

const evaluationPredictions = computed(() =>
  responseQueue.value
    .filter((item) => item.status === "success" && item.parsed)
    .map((item) => ({ imagePath: item.imagePath, parsed: normalizeParsedResult(item.parsed, mappingModel.value) })),
);
const selectedSuccessfulPredictions = computed(() => {
  const selected = responseQueue.value.filter((item) => item.selected && item.status === "success" && item.parsed);
  const source = selected.length ? selected : responseQueue.value.filter((item) => item.status === "success" && item.parsed);
  return source.map((item) => ({ imagePath: item.imagePath, parsed: normalizeParsedResult(item.parsed, mappingModel.value) }));
});

const conversionPredictions = computed(() => selectedSuccessfulPredictions.value);

const namesSummary = computed(() => {
  if (!gtNames.value.length) return "No names configured. ";
  const visible = gtNames.value.slice(0, 8).join(", ");
  const suffix = gtNames.value.length > 8 ? " +" + String(gtNames.value.length - 8) + " more" : "";
  return String(gtNames.value.length) + ": " + visible + suffix + ".";
});

const conversionCanRun = computed(() => {
  if (!gtNames.value.length || !conversionTargetFormat.value) return false;
  if (conversionMode.value === "pred") return conversionPredictions.value.length > 0;
  return Boolean(evaluationImageDir.value && gtLabelDir.value && gtFormat.value);
});

const currentPipelineCacheName = computed(() => String(editor.name || persistedPipelineName.value || "").trim());
const currentCacheSourcePath = computed(() => selectedImagePath.value || editor.inputPath || "");
const currentCacheBucket = computed(() => cacheBucketForPath(currentCacheSourcePath.value));
const currentCachePath = computed(() => {
  const pipeline = currentPipelineCacheName.value;
  const bucket = currentCacheBucket.value;
  if (pipeline && bucket) return "data/.cache/" + pipeline + "/" + bucket;
  if (pipeline) return "data/.cache/" + pipeline + "/<select-image-or-input>";
  return "data/.cache/<save-current-pipeline>/<select-image-or-input>";
});
const currentConversionCachePath = computed(() => currentCachePath.value + "/" + conversionTargetFormat.value);
const predictionStats = computed(() => {
  const predictions = evaluationPredictions.value;
  const instances = predictions.reduce((total, item) => total + (Array.isArray(item.parsed) ? item.parsed.length : item.parsed ? 1 : 0), 0);
  return { images: predictions.length, instances };
});

const cacheAllSelected = computed(() => cacheItems.value.length > 0 && selectedCacheBuckets.value.length === cacheItems.value.length);

const evaluationCanRun = computed(() =>
  Boolean(evaluationPredictions.value.length && gtLabelDir.value && gtNames.value.length && editor.inputPath),
);

const evaluationImageDir = computed(() => {
  const path = String(editor.inputPath || "").trim();
  if (!path) return "";
  if (responseQueue.value.length === 1 && responseQueue.value[0]?.imagePath === path) {
    return parentDirectoryPath(path);
  }
  return path;
});

const evaluationClassRows = computed(() => {
  const perClass = evaluationResult.value?.metrics?.per_class || {};
  return Object.entries(perClass).map(([name, metrics]) => ({ name, ...metrics }));
});
function isEvaluationApKey(key) {
  return key.startsWith("mAP") && !key.includes("-") && key !== "mAP";
}

function isEvaluationApRangeKey(key) {
  return key.startsWith("mAP") && key.includes("-");
}

const evaluationApKey = computed(() => {
  const metrics = evaluationResult.value?.metrics || {};
  return Object.keys(metrics).find(isEvaluationApKey) || "mAP";
});

const evaluationApRangeKey = computed(() => {
  const metrics = evaluationResult.value?.metrics || {};
  return Object.keys(metrics).find(isEvaluationApRangeKey) || `${evaluationApKey.value}-95`;
});

const filteredSelectedCount = computed(() =>
  filteredResponseQueue.value.filter((item) => item.selected).length,
);

const filteredSelectAllChecked = computed(() =>
  filteredResponseQueue.value.length > 0 && filteredSelectedCount.value === filteredResponseQueue.value.length,
);

const filteredSelectAllIndeterminate = computed(() =>
  filteredSelectedCount.value > 0 && filteredSelectedCount.value < filteredResponseQueue.value.length,
);

const responseGridStyle = computed(() => ({
  gridTemplateColumns: `minmax(360px, ${responseLeftPercent.value}fr) 8px minmax(320px, ${100 - responseLeftPercent.value}fr)`,
}));

const responseStatusCounts = computed(() =>
  responseQueue.value.reduce(
    (counts, item) => {
      counts[item.status] += 1;
      return counts;
    },
    { new: 0, success: 0, failed: 0, abort: 0 },
  ),
);


const collectionGroups = computed(() => {
  const groupsMap = new Map();
  for (const group of pipelineGroups.value) {
    groupsMap.set(group.name, []);
  }
  if (!groupsMap.has(ungroupedLabel)) {
    groupsMap.set(ungroupedLabel, []);
  }
  if (!groupsMap.has(deletedGroupLabel)) {
    groupsMap.set(deletedGroupLabel, []);
  }
  for (const item of pipelineItems.value) {
    const groupName = item.groupName || ungroupedLabel;
    if (!groupsMap.has(groupName)) {
      groupsMap.set(groupName, []);
    }
    groupsMap.get(groupName).push({
      key: item.name,
      label: item.displayName,
      subtitle: item.name,
      badge: item.method,
      badgeClass: methodClass(item.method),
      raw: item,
    });
  }
  const groupEntries = Array.from(groupsMap.entries()).sort(([leftName], [rightName]) => {
    if (leftName === ungroupedLabel) return -1;
    if (rightName === ungroupedLabel) return 1;
    if (leftName === deletedGroupLabel) return 1;
    if (rightName === deletedGroupLabel) return -1;
    return leftName.localeCompare(rightName, undefined, { numeric: true, sensitivity: "base" });
  });
  return groupEntries.map(([name, items]) => ({
    name,
    items,
    canRename: name !== ungroupedLabel && name !== deletedGroupLabel,
    canDelete: name !== ungroupedLabel && name !== deletedGroupLabel,
    isTrash: name === deletedGroupLabel,
  }));
});

const savedBodyJson = computed(() => parseSavedText(savedAssetTexts.body));
const savedResponseJson = computed(() => parseSavedText(savedAssetTexts.response));
const jsonDependencyReady = computed(
  () => hasJsonContent(savedBodyJson.value) && hasJsonContent(savedResponseJson.value),
);

const requestTabs = computed(() =>
  baseRequestTabs.map((tab) => {
    if (tab.id === "mapping" || tab.id === "post-config") {
      return {
        ...tab,
        disabled: !jsonDependencyReady.value,
        disabledReason: "Body JSON and Response JSON are required first.",
      };
    }
    return { ...tab, disabled: false, disabledReason: "" };
  }),
);

const bodyFieldPathOptions = computed(() => {
  return collectObjectPaths(hasJsonContent(bodyTemplate.value) ? bodyTemplate.value : savedBodyJson.value);
});
const responseMappingPathOptions = computed(() => {
  return collectResponseMappingPaths(
    hasJsonContent(responseTemplate.value) ? responseTemplate.value : savedResponseJson.value,
    mappingModel.value,
  );
});

const normalizedParsedResult = computed(() => normalizeParsedResult(selectedResult.value?.parsed, mappingModel.value));

watch(jsonDependencyReady, (ready) => {
  if (!ready && (activeRequestTab.value === "mapping" || activeRequestTab.value === "post-config")) {
    activeRequestTab.value = hasJsonContent(savedBodyJson.value) ? "response" : "body";
  }
});

watch(selectedImagePath, () => {
  scrollSelectedResponseIntoView();
  refreshCurrentGTVisualizationIfVisible();
});

watch(previewMode, (mode) => {
  if (mode === "gt") {
    refreshCurrentGTVisualizationIfVisible();
  }
});

function focusPreviewNavigation() {
  previewStageRef.value?.focus({ preventScroll: true });
}

function selectPreviewByOffset(offset) {
  const visibleItems = filteredResponseQueue.value.length ? filteredResponseQueue.value : responseQueue.value;
  if (!visibleItems.length) {
    return;
  }
  const currentIndex = visibleItems.findIndex((item) => item.imagePath === selectedImagePath.value);
  const baseIndex = currentIndex >= 0 ? currentIndex : offset > 0 ? -1 : visibleItems.length;
  const nextIndex = Math.min(visibleItems.length - 1, Math.max(0, baseIndex + offset));
  const nextItem = visibleItems[nextIndex];
  if (nextItem?.imagePath && nextItem.imagePath !== selectedImagePath.value) {
    selectedImagePath.value = nextItem.imagePath;
  }
}

function scrollSelectedResponseIntoView() {
  nextTick(() => {
    const shell = responseListShellRef.value;
    if (!shell || !selectedImagePath.value) {
      return;
    }
    const selectedRow = Array.from(shell.querySelectorAll("[data-response-image-path]")).find(
      (element) => element.dataset.responseImagePath === selectedImagePath.value,
    );
    selectedRow?.scrollIntoView({ block: "nearest", inline: "nearest" });
  });
}

function createEmptyEditor() {
  return {
    name: "",
    displayName: "",
    groupName: ungroupedLabel,
    url: "",
    method: "POST",
    transport: "http",
    inputPath: "",
    imageFieldPath: "image",
    imageSource: "base64",
    assetPaths: {},
    connectTimeout: 3,
    readTimeout: 30,
  };
}

function createDefaultMappingModel() {
  return {
    collectionPath: "",
    itemPath: "",
    labelPath: null,
    classIdPath: null,
    confPath: null,
    bboxPath: null,
    bboxPaths: [null, null, null, null],
    bboxInputMode: "list",
    bboxCoordinateType: "xyxy",
    bboxIsCenter: false,
    bboxCast: "float",
    plotFields: ["label", "conf"],
    extraFields: [],
  };
}

function createDefaultPostConfig() {
  return {
    connectTimeout: 3,
    readTimeout: 30,
    placeholderPaths: {
      timestamp: null,
      image_b64: null,
      image_width: null,
      image_height: null,
    },
    placeholderTypes: {
      timestamp: "int",
      image_b64: "string",
      image_width: "int",
      image_height: "int",
    },
  };
}

function createDisplayName(path, fallback) {
  return path || fallback;
}

function createRootNode(path, fallbackName = "Data Root") {
  return createTreeNode({
    name: createDisplayName(path, fallbackName),
    path,
    type: "directory",
    hasChildren: true,
  });
}

async function loadAppConfig() {
  const response = await fetch("/api/config");
  if (!response.ok) {
    throw await responseToError(response, "Failed to load app config");
  }
  const data = await response.json();
  appConfig.filesystemRoot = data.filesystemRoot || "";
  appConfig.datasetsRoot = data.datasetsRoot || appConfig.filesystemRoot || "";
  appConfig.frontendDist = data.frontendDist || "";
  rootNode.value = createRootNode(appConfig.filesystemRoot, "Data Root");
  uploadParentPath.value = appConfig.datasetsRoot;
  uploadSelectionPath.value = appConfig.datasetsRoot;
}

function createTreeNode(node) {
  return {
    ...node,
    expanded: false,
    loading: false,
    loadingMore: false,
    error: "",
    children: [],
    childrenLoaded: node.childrenLoaded ?? false,
    childrenOffset: node.childrenOffset ?? 0,
    hasMoreChildren: node.hasMoreChildren ?? false,
  };
}

function switchRequestTab(tab) {
  if (tab.disabled) {
    formError.value = tab.disabledReason;
    return;
  }
  formError.value = "";
  activeRequestTab.value = tab.id;
}


function resetEditor(data = null, hydrateSaved = false) {
  const nextEditor = data || createEmptyEditor();
  persistedPipelineName.value = hydrateSaved ? nextEditor.name || "" : "";
  Object.assign(editor, {
    ...createEmptyEditor(),
    ...nextEditor,
    groupName: nextEditor.groupName || ungroupedLabel,
  });
  headerTemplate.value = nextEditor.headerTemplate || {};
  const migratedBody = migrateDynamicBodyPlaceholders(nextEditor.bodyTemplate || {});
  bodyTemplate.value = nextEditor.bodyTemplate || {};
  responseTemplate.value = nextEditor.templateInput || {};
  mappingModel.value = mappingFromResponseMapping(nextEditor.responseMapping || {});
  postConfigModel.value = mergeDetectedPostConfig(
    normalizePostConfig(nextEditor.postConfig, nextEditor.connectTimeout, nextEditor.readTimeout),
    migratedBody,
  );
  const assetPaths = nextEditor.assetPaths || {};
  savedAssetTexts.header = hydrateSaved && assetPaths.header ? stringify(headerTemplate.value) : "";
  savedAssetTexts.body = hydrateSaved && assetPaths.body ? stringify(bodyTemplate.value) : "";
  savedAssetTexts.response = hydrateSaved && assetPaths.response ? stringify(responseTemplate.value) : "";
  savedAssetTexts.mapping = hydrateSaved && assetPaths.mapping ? stringify(mappingToStorage(mappingModel.value)) : "";
  savedAssetTexts.post_config = hydrateSaved && assetPaths.post_config ? stringify(postConfigModel.value) : "";
}

const dynamicBodyPlaceholders = {
  image_base64: { key: "image_b64", type: "string", emptyValue: "" },
  image_b64: { key: "image_b64", type: "string", emptyValue: "" },
  unix_timestamp: { key: "timestamp", type: "int", emptyValue: 0 },
  timestamp: { key: "timestamp", type: "int", emptyValue: 0 },
  image_width: { key: "image_width", type: "int", emptyValue: 0 },
  image_height: { key: "image_height", type: "int", emptyValue: 0 },
};

function migrateDynamicBodyPlaceholders(source) {
  const placeholderPaths = {};
  const placeholderTypes = {};
  const visit = (value, path = "") => {
    if (Array.isArray(value)) {
      return value.map((item, index) => visit(item, path ? path + "." + index : String(index)));
    }
    if (value && typeof value === "object") {
      return Object.fromEntries(
        Object.entries(value).map(([key, item]) => [key, visit(item, path ? path + "." + key : key)]),
      );
    }
    if (typeof value !== "string") {
      return value;
    }
    const match = value.match(/^\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}$/);
    const config = match ? dynamicBodyPlaceholders[match[1]] : null;
    if (!config) {
      return value;
    }
    if (!placeholderPaths[config.key]) {
      placeholderPaths[config.key] = path;
      placeholderTypes[config.key] = config.type;
    }
    return Array.isArray(config.emptyValue) ? [...config.emptyValue] : config.emptyValue;
  };
  return { template: visit(source), placeholderPaths, placeholderTypes };
}

function mergeDetectedPostConfig(current, detected) {
  const normalized = normalizePostConfig(current);
  return {
    ...normalized,
    placeholderPaths: {
      ...normalized.placeholderPaths,
      ...detected.placeholderPaths,
    },
    placeholderTypes: {
      ...normalized.placeholderTypes,
      ...detected.placeholderTypes,
    },
  };
}

function mappingFromResponseMapping(value) {
  const plotFields = Array.isArray(value?.plotFields) ? value.plotFields : ["label", "conf"];
  return {
    ...createDefaultMappingModel(),
    ...value,
    plotFields,
    collectionPath: value?.collectionPaths?.[0] || value?.collectionPath || "",
    itemPath: value?.itemPath || "",
    extraFields: (value?.extraFields || []).map((field, index) => ({
      id: `extra-${index}-${field.name || "field"}`,
      name: field.name || "",
      path: field.path || "",
      cast: field.cast || "string",
      plot: plotFields.includes(field.name),
    })),
  };
}

function normalizePostConfig(value, connectTimeout, readTimeout) {
  const defaults = createDefaultPostConfig();
  const supportedKeys = Object.keys(defaults.placeholderPaths);
  return {
    ...defaults,
    ...(value || {}),
    connectTimeout: Number(value?.connectTimeout ?? connectTimeout ?? 3),
    readTimeout: Number(value?.readTimeout ?? readTimeout ?? 30),
    placeholderPaths: Object.fromEntries(
      supportedKeys.map((key) => [key, value?.placeholderPaths?.[key] ?? defaults.placeholderPaths[key]]),
    ),
    placeholderTypes: Object.fromEntries(
      supportedKeys.map((key) => [key, value?.placeholderTypes?.[key] ?? defaults.placeholderTypes[key]]),
    ),
  };
}

async function fetchChildren(path, offset = 0, filter = "") {
  const params = new URLSearchParams({
    offset: String(offset),
    limit: String(directoryPageSize),
  });
  if (path) {
    params.set("path", path);
  }
  if (filter) {
    params.set("filter", filter);
  }
  const response = await fetch(`/api/tree?${params.toString()}`);
  if (!response.ok) {
    throw await responseToError(response, "Failed to read directory");
  }
  return response.json();
}

async function fetchFilteredChildren(path, filter) {
  const children = [];
  let offset = 0;
  let hasMore = true;
  while (hasMore) {
    const data = await fetchChildren(path, offset, filter);
    children.push(...data.children.map(createTreeNode));
    offset = data.offset + data.children.length;
    hasMore = data.hasMore && data.children.length > 0;
  }
  return children;
}

async function fetchJsonOnlyChildren(path, filter = "") {
  const children = await fetchFilteredChildren(path, filter);
  return children.filter((item) => item.type === "directory" || item.name.toLowerCase().endsWith(".json"));
}

async function loadChildren(node, force = false) {
  if (node.type !== "directory" || node.loading) {
    return;
  }
  if (node.childrenLoaded && !force) {
    return;
  }
  node.loading = true;
  node.error = "";
  try {
    const data = await fetchChildren(node.path, force ? 0 : node.childrenOffset);
    node.path = data.path;
    if (node === rootNode.value) {
      node.name = createDisplayName(appConfig.filesystemRoot, "Data Root");
    }
    node.children = data.children.map(createTreeNode);
    node.childrenOffset = data.offset + data.children.length;
    node.hasMoreChildren = data.hasMore;
    node.childrenLoaded = true;
  } catch (error) {
    node.error = error.message;
  } finally {
    node.loading = false;
  }
}

async function loadMoreChildren(node) {
  if (node.type !== "directory" || node.loadingMore || !node.hasMoreChildren) {
    return;
  }
  node.loadingMore = true;
  node.error = "";
  try {
    const data = await fetchChildren(node.path, node.childrenOffset);
    node.children.push(...data.children.map(createTreeNode));
    node.childrenOffset = data.offset + data.children.length;
    node.hasMoreChildren = data.hasMore;
  } catch (error) {
    node.error = error.message;
  } finally {
    node.loadingMore = false;
  }
}

async function toggleNode(node) {
  if (node.type !== "directory") {
    return;
  }
  node.expanded = !node.expanded;
  if (node.expanded) {
    await loadChildren(node);
  }
}

function selectUploadParent(node) {
  uploadSelectionPath.value = node.path;
  uploadParentPath.value = node.type === "directory" ? node.path : parentDirectoryPath(node.path);
}

async function handleUploadComplete(payload) {
  const uploadedItems = payload?.items || [];
  if (!uploadedItems.length) return;

  const directoryNode = findTreeNode(rootNode.value, payload.directory);
  if (directoryNode) {
    directoryNode.expanded = true;
    directoryNode.childrenLoaded = false;
    await loadChildren(directoryNode, true);
    for (const item of uploadedItems) ensureUploadedPathVisible(directoryNode, item.path);
  } else {
    await reloadRoot();
  }

  const lastUploadedPath = uploadedItems[uploadedItems.length - 1]?.path;
  if (lastUploadedPath) {
    uploadSelectionPath.value = lastUploadedPath;
    uploadParentPath.value = parentDirectoryPath(lastUploadedPath);
  }
}

function findTreeNode(node, path) {
  if (!node) return null;
  if (normalizeFilesystemPath(node.path) === normalizeFilesystemPath(path)) return node;
  for (const child of node.children || []) {
    const found = findTreeNode(child, path);
    if (found) return found;
  }
  return null;
}

function ensureUploadedPathVisible(directoryNode, uploadedPath) {
  const directoryPath = normalizeFilesystemPath(directoryNode.path);
  const fullPath = normalizeFilesystemPath(uploadedPath);
  if (!fullPath.startsWith(directoryPath + "/")) return;

  const parts = fullPath.slice(directoryPath.length + 1).split("/").filter(Boolean);
  let current = directoryNode;
  parts.forEach((part, index) => {
    const nodePath = current.path.replace(/[\\/]$/, "") + "/" + part;
    let child = (current.children || []).find((item) => normalizeFilesystemPath(item.path) === normalizeFilesystemPath(nodePath));
    if (!child) {
      child = createTreeNode({ name: part, path: nodePath, type: index === parts.length - 1 ? "file" : "directory", hasChildren: index < parts.length - 1 });
      current.children.push(child);
      current.children.sort((left, right) => (left.type !== right.type ? (left.type === "directory" ? -1 : 1) : left.name.localeCompare(right.name, undefined, { numeric: true })));
    }
    if (child.type === "directory") child.expanded = true;
    current = child;
  });
}

function cacheBucketForPath(rawPath) {
  const normalized = normalizeFilesystemPath(rawPath);
  if (!normalized) return "";
  const parts = normalized.split("/").filter(Boolean);
  const lastPart = parts[parts.length - 1] || "cache";
  const looksLikeFile = lastPart.includes(".");
  const bucketParts = looksLikeFile ? parts.slice(0, -1) : parts;
  const currentName = bucketParts[bucketParts.length - 1] || "cache";
  const parentName = bucketParts[bucketParts.length - 2] || "";
  return sanitizeCacheName((parentName ? parentName + "_" : "") + currentName);
}

function sanitizeCacheName(value) {
  return String(value || "cache").replace(/[^a-zA-Z0-9_.-]+/g, "_").replace(/^[._-]+|[._-]+$/g, "") || "cache";
}

function normalizeFilesystemPath(path) {
  let normalized = String(path || "").split("\\").join("/");
  while (normalized.length > 1 && normalized.endsWith("/")) normalized = normalized.slice(0, -1);
  return normalized;
}

function openGTSettingsDialog() {
  gtSettingsDraft.labelDir = gtLabelDir.value;
  gtSettingsDraft.format = gtFormat.value;
  gtSettingsDraft.names = gtNames.value.join("\n");
  gtSettingsDialog.visible = true;
  loadPipelineCache();
}

function closeGTSettingsDialog() {
  gtSettingsDialog.visible = false;
}

async function applyGTSettings() {
  gtLabelDir.value = String(gtSettingsDraft.labelDir || "").trim();
  gtFormat.value = gtSettingsDraft.format || "yolo";
  gtNames.value = gtSettingsDraft.names.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
  responseQueue.value = responseQueue.value.map((item) => ({ ...item, gtCachePath: null, gtSavedPath: null, gtError: "" }));
  gtSettingsDialog.visible = false;
  bumpVisualizationRefresh();
  await refreshCurrentGTVisualizationIfVisible();
}

async function openGTBrowser() {
  gtBrowser.visible = true;
  gtBrowser.selectedPath = gtSettingsDialog.visible ? gtSettingsDraft.labelDir : gtLabelDir.value;
  gtRootNode.value = createRootNode(appConfig.filesystemRoot, "Data Root");
  gtRootNode.value.expanded = true;
  await loadChildren(gtRootNode.value, true);
}

function closeGTBrowser() {
  gtBrowser.visible = false;
}

function highlightGTPath(node) {
  gtBrowser.selectedPath = node.type === "directory" ? node.path : parentDirectoryPath(node.path);
}

async function selectGTLabelFolder(node) {
  if (node.type !== "directory") return;
  gtBrowser.selectedPath = node.path;
  gtBrowser.visible = false;
  if (gtSettingsDialog.visible) {
    gtSettingsDraft.labelDir = node.path;
    return;
  }
  gtLabelDir.value = node.path;
  responseQueue.value = responseQueue.value.map((item) => ({ ...item, gtCachePath: null, gtSavedPath: null, gtError: "" }));
  bumpVisualizationRefresh();
}

async function reloadGTRoot() {
  if (!gtRootNode.value) return;
  gtRootNode.value.childrenLoaded = false;
  gtRootNode.value.expanded = true;
  await loadChildren(gtRootNode.value, true);
}

async function generateGTVisualizations() {
  if (!editor.name || !gtLabelDir.value || !gtNames.value.length || !responseQueue.value.length) return;
  gtGenerating.value = true;
  runError.value = "";
  try {
    const response = await fetch(`/api/pipelines/${encodeURIComponent(editor.name)}/visualizations/gt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        imagePaths: responseQueue.value.map((item) => item.imagePath),
        labelDir: gtLabelDir.value,
        format: gtFormat.value,
        names: gtNames.value,
      }),
    });
    if (!response.ok) throw await responseToError(response, "Failed to generate GT visualizations");
    const data = await response.json();
    const resultMap = new Map((data.items || []).map((item) => [item.imagePath, item]));
    responseQueue.value = responseQueue.value.map((item) => {
      const result = resultMap.get(item.imagePath);
      return result ? { ...item, gtCachePath: result.cachePath || null, gtSavedPath: null, gtError: result.error || "" } : item;
    });
    bumpVisualizationRefresh();
  } catch (error) {
    runError.value = error.message;
  } finally {
    gtGenerating.value = false;
  }
}

async function runResultEvaluation() {
  if (!evaluationCanRun.value || evaluationRunning.value) return;
  evaluationRunning.value = true;
  evaluationError.value = "";
  try {
    const response = await fetch("/api/dsetkit/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        imageDir: evaluationImageDir.value,
        labelDir: gtLabelDir.value,
        sourceFormat: gtFormat.value,
        names: gtNames.value,
        predictions: evaluationPredictions.value,
        confThreshold: Number(evaluationConfThreshold.value),
        iouThreshold: Number(evaluationIouThreshold.value),
      }),
    });
    if (!response.ok) throw await responseToError(response, "Failed to evaluate results");
    evaluationResult.value = await response.json();
  } catch (error) {
    evaluationError.value = error.message;
  } finally {
    evaluationRunning.value = false;
  }
}
async function runAnnotationConversion() {
  if (!conversionCanRun.value || conversionRunning.value) return;
  conversionRunning.value = true;
  conversionError.value = "";
  conversionResult.value = null;
  try {
    const isPred = conversionMode.value === "pred";
    const endpoint = isPred ? "/api/dsetkit/convert/pred" : "/api/dsetkit/convert";
    const payload = isPred
      ? {
          targetFormat: conversionTargetFormat.value,
          names: gtNames.value,
          predictions: conversionPredictions.value,
          pipelineName: editor.name,
          cacheBucket: currentCacheBucket.value,
        }
      : {
          imageDir: evaluationImageDir.value,
          labelDir: gtLabelDir.value,
          sourceFormat: gtFormat.value,
          targetFormat: conversionTargetFormat.value,
          names: gtNames.value,
          pipelineName: editor.name,
          cacheBucket: currentCacheBucket.value,
        };
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw await responseToError(response, "Failed to convert annotations");
    conversionResult.value = await response.json();
  } catch (error) {
    conversionError.value = error.message;
  } finally {
    conversionRunning.value = false;
  }
}

async function refreshCurrentGTVisualizationIfVisible() {
  if (previewMode.value === "gt" && selectedImagePath.value) {
    await refreshCurrentGTVisualization();
  }
}

async function refreshCurrentVisualization() {
  if (previewMode.value === "pred") {
    await refreshCurrentPredVisualization();
  } else {
    await refreshCurrentGTVisualization();
  }
}
async function refreshCurrentPredVisualization() {
  const item = selectedResult.value;
  if (!editor.name || !item?.imagePath || !item?.parsed || predRefreshing.value) return;
  predRefreshing.value = true;
  runError.value = "";
  try {
    const response = await fetch(`/api/pipelines/${encodeURIComponent(editor.name)}/visualizations/pred`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ imagePath: item.imagePath, parsed: item.parsed }),
    });
    if (!response.ok) throw await responseToError(response, "Failed to refresh Pred visualization");
    const data = await response.json();
    const result = data.items?.[0];
    if (result?.error) throw new Error(result.error);
    responseQueue.value = responseQueue.value.map((queueItem) =>
      queueItem.imagePath === item.imagePath
        ? { ...queueItem, predCachePath: result?.cachePath || queueItem.predCachePath || null, predSavedPath: null }
        : queueItem,
    );
    bumpVisualizationRefresh();
  } catch (error) {
    runError.value = error.message;
  } finally {
    predRefreshing.value = false;
  }
}

async function refreshCurrentGTVisualization() {
  const item = selectedResult.value;
  if (!editor.name || !item?.imagePath || !gtLabelDir.value || !gtNames.value.length || gtRefreshing.value || gtGenerating.value) return;
  gtRefreshing.value = true;
  runError.value = "";
  try {
    const response = await fetch(`/api/pipelines/${encodeURIComponent(editor.name)}/visualizations/gt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        imagePaths: [item.imagePath],
        labelDir: gtLabelDir.value,
        format: gtFormat.value,
        names: gtNames.value,
      }),
    });
    if (!response.ok) throw await responseToError(response, "Failed to refresh GT visualization");
    const data = await response.json();
    const result = data.items?.[0];
    responseQueue.value = responseQueue.value.map((queueItem) =>
      queueItem.imagePath === item.imagePath
        ? { ...queueItem, gtCachePath: result?.cachePath || null, gtSavedPath: null, gtError: result?.error || "" }
        : queueItem,
    );
    bumpVisualizationRefresh();
  } catch (error) {
    runError.value = error.message;
  } finally {
    gtRefreshing.value = false;
  }
}

async function downloadVisualizationFolder() {
  const items = downloadableVisualizationItems.value;
  if (!items.length || visualizationDownloading.value) return;
  if (!window.showDirectoryPicker) {
    runError.value = "Your browser does not support choosing a local download folder.";
    return;
  }

  visualizationDownloading.value = true;
  visualizationDownloadError.value = "";
  try {
    const rootHandle = await window.showDirectoryPicker({ mode: "readwrite" });
    const folderName = previewMode.value === "pred" ? "pred" : "GT";
    const outputHandle = await rootHandle.getDirectoryHandle(folderName, { create: true });
    for (const item of items) {
      const blob = await fetchVisualizationBlob(item.downloadPath);
      const fileHandle = await outputHandle.getFileHandle(downloadFileName(item), { create: true });
      const writable = await fileHandle.createWritable();
      await writable.write(blob);
      await writable.close();
    }
  } catch (error) {
    if (error?.name !== "AbortError") {
      visualizationDownloadError.value = error.message || "Download failed.";
      runError.value = visualizationDownloadError.value;
    }
  } finally {
    visualizationDownloading.value = false;
  }
}

async function fetchVisualizationBlob(path) {
  const response = await fetch(visualizationContentUrl(path));
  if (!response.ok) {
    throw await responseToError(response, "Failed to download visualization");
  }
  return response.blob();
}

function visualizationContentUrl(path) {
  const params = new URLSearchParams({ path });
  return "/api/pipelines/" + encodeURIComponent(editor.name) + "/visualizations/content?" + params.toString();
}

function downloadFileName(item) {
  return baseName(item.downloadPath) || (baseName(item.imagePath) || "annotation") + ".jpg";
}

async function selectPath(node) {
  activePath.value = node.path;
  editor.inputPath = node.path;
  showFileBrowser.value = false;
  await loadResponseQueue(node.path);
}

function selectAssetPath(node) {
  assetReader.selectedPath = node.path;
}

async function reloadRoot() {
  rootNode.value.childrenLoaded = false;
  rootNode.value.expanded = true;
  await loadChildren(rootNode.value, true);
}

async function openFileBrowser() {
  showFileBrowser.value = true;
  if (!rootNode.value.childrenLoaded) {
    rootNode.value.expanded = true;
    await loadChildren(rootNode.value);
  }
}

function closeFileBrowser() {
  showFileBrowser.value = false;
}

async function loadPipelineCache() {
  if (!editor.name) return;
  cacheLoading.value = true;
  cacheError.value = "";
  try {
    const response = await fetch(`/api/pipelines/${encodeURIComponent(editor.name)}/cache`);
    if (!response.ok) throw await responseToError(response, "Failed to load cache folders");
    const data = await response.json();
    cacheItems.value = data.items || [];
    selectedCacheBuckets.value = selectedCacheBuckets.value.filter((name) => cacheItems.value.some((item) => item.name === name));
  } catch (error) {
    cacheError.value = error.message;
  } finally {
    cacheLoading.value = false;
  }
}

function toggleCacheBucket(name, selected) {
  const current = new Set(selectedCacheBuckets.value);
  if (selected) current.add(name);
  else current.delete(name);
  selectedCacheBuckets.value = [...current];
}

function toggleAllCacheBuckets(selected) {
  selectedCacheBuckets.value = selected ? cacheItems.value.map((item) => item.name) : [];
}

async function deleteSelectedCacheBuckets() {
  if (!editor.name || !selectedCacheBuckets.value.length) return;
  cacheError.value = "";
  try {
    const response = await fetch(`/api/pipelines/${encodeURIComponent(editor.name)}/cache`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ buckets: selectedCacheBuckets.value }),
    });
    if (!response.ok) throw await responseToError(response, "Failed to delete cache folders");
    selectedCacheBuckets.value = [];
    await loadPipelineCache();
  } catch (error) {
    cacheError.value = error.message;
  }
}

async function openResultsBrowser() {
  if (!editor.name) {
    return;
  }
  gtSettingsDialog.visible = false;
  resultsBrowser.visible = true;
  resultsBrowser.selectedPath = "";
  resultsRootNode.value = createRootNode(appConfig.filesystemRoot, "Data Root");
  resultsRootNode.value.expanded = true;
  await loadResultsRootDirectories();
}

function closeResultsBrowser() {
  resultsBrowser.visible = false;
  resultsBrowser.selectedPath = "";
}

function selectResultsPath(node) {
  if (node.type === "directory") {
    resultsBrowser.selectedPath = node.path;
  }
}

async function loadResultsRootDirectories() {
  if (!resultsRootNode.value) {
    return;
  }
  resultsRootNode.value.loading = true;
  resultsRootNode.value.error = "";
  try {
    const children = await fetchFilteredChildren(resultsRootNode.value.path, "");
    resultsRootNode.value.children = children
      .filter((item) => item.type === "directory")
      .sort((left, right) => right.name.localeCompare(left.name, undefined, { numeric: true }));
    resultsRootNode.value.childrenLoaded = true;
    resultsRootNode.value.childrenOffset = resultsRootNode.value.children.length;
    resultsRootNode.value.hasMoreChildren = false;
  } catch (error) {
    resultsRootNode.value.error = error.message;
  } finally {
    resultsRootNode.value.loading = false;
  }
}

async function reloadResultsRoot() {
  await loadResultsRootDirectories();
}

async function loadSelectedResultsFolder() {
  if (!resultsBrowser.selectedPath) {
    return;
  }
  await loadSavedRunResults(editor.inputPath, resultsBrowser.selectedPath);
  closeResultsBrowser();
}

function openAssetReader(kind) {
  assetReader.visible = true;
  assetReader.kind = kind;
  assetReader.selectedPath = editor.assetPaths?.[kind] || "";
}

function closeAssetReader() {
  assetReader.visible = false;
  assetReader.selectedPath = "";
}

async function readSelectedAsset() {
  try {
    const response = await fetch(`/api/pipelines/assets?${new URLSearchParams({ path: assetReader.selectedPath }).toString()}`);
    if (!response.ok) {
      throw await responseToError(response, "Failed to read asset");
    }
    const data = await response.json();
    if (assetReader.kind === "mapping") {
      mappingModel.value = mappingFromResponseMapping(data.content || {});
      savedAssetTexts.mapping = data.text || stringify(data.content);
    } else {
      postConfigModel.value = normalizePostConfig(data.content || {}, editor.connectTimeout, editor.readTimeout);
      savedAssetTexts.post_config = data.text || stringify(data.content);
    }
    editor.assetPaths = {
      ...(editor.assetPaths || {}),
      [assetReader.kind]: data.path || assetReader.selectedPath || null,
    };
    formSuccess.value = "Config loaded successfully";
    closeAssetReader();
  } catch (error) {
    formError.value = error.message;
    window.alert(`Failed to load pipeline: ${error.message}`);
  }
}

function createNewPipeline() {
  clearCurrentPipelineState();
  resetEditor({ ...createEmptyEditor(), inputPath: editor.inputPath }, false);
}

function clearCurrentPipelineState() {
  formError.value = "";
  formSuccess.value = "";
  runError.value = "";
  runResult.value = null;
  responseQueue.value = [];
  selectedImagePath.value = "";
}

async function createAndSaveNewPipeline(payload = {}) {
  clearCurrentPipelineState();
  const groupName = String(payload?.groupName || ungroupedLabel).trim() || ungroupedLabel;
  const name = nextAvailablePipelineName("new_pipeline");
  resetEditor(
    {
      ...createEmptyEditor(),
      name,
      displayName: name,
      groupName,
      url: "http://localhost",
      inputPath: editor.inputPath,
    },
    false,
  );
  await savePipeline();
}

async function clonePipelineFromCollection(payload = {}) {
  const item = payload?.item;
  if (!item?.name) {
    return;
  }
  if (item.name !== editor.name) {
    await loadPipeline(item);
  }
  await cloneCurrentPipeline();
}

async function cloneCurrentPipeline() {
  formError.value = "";
  formSuccess.value = "";
  const sourceName = String(editor.name || "").trim();
  if (!sourceName) {
    formError.value = "Please select or save a pipeline before cloning.";
    window.alert(formError.value);
    return;
  }
  const clonedName = sourceName + "_copy";
  if (pipelineItems.value.some((item) => item.name === clonedName)) {
    formError.value = 'Pipeline "' + clonedName + '" already exists.';
    window.alert(formError.value);
    return;
  }
  const currentImagePath = editor.inputPath;
  resetEditor(
    {
      ...buildPipelinePayload(),
      originalName: null,
      name: clonedName,
      displayName: String(editor.displayName || sourceName) + "_copy",
      groupName: editor.groupName || ungroupedLabel,
      inputPath: currentImagePath,
    },
    false,
  );
  await savePipeline();
}

function nextAvailablePipelineName(baseName) {
  const existing = new Set(pipelineItems.value.map((item) => item.name));
  if (!existing.has(baseName)) {
    return baseName;
  }
  let suffix = 2;
  while (existing.has(baseName + "_" + suffix)) {
    suffix += 1;
  }
  return baseName + "_" + suffix;
}

async function loadPipelineList() {
  const response = await fetch("/api/pipelines");
  if (!response.ok) {
    throw await responseToError(response, "Failed to read pipeline list");
  }
  const data = await response.json();
  pipelineItems.value = data.items || [];
  pipelineGroups.value = data.groups || [];
}

async function loadPipeline(itemOrName) {
  formError.value = "";
  formSuccess.value = "";
  const name = typeof itemOrName === "string" ? itemOrName : itemOrName?.name;
  if (!name) {
    return;
  }
  try {
    const response = await fetch(`/api/pipelines/${encodeURIComponent(name)}`);
    if (!response.ok) {
      throw await responseToError(response, "Failed to load pipeline");
    }
    const data = await response.json();
    const currentImagePath = editor.inputPath;
    resetEditor({
      ...data,
      inputPath: currentImagePath,
    }, true);
    activeWorkspaceView.value = "request";
    if (editor.inputPath) {
      await loadResponseQueue(editor.inputPath);
    }
  } catch (error) {
    formError.value = error.message;
  }
}

async function submitCreateGroup(rawName) {
  const name = String(rawName || "").trim();
  if (!name) {
    return;
  }
  const groupNameError = validateGroupName(name);
  if (groupNameError) {
    formError.value = groupNameError;
    window.alert(groupNameError);
    return;
  }
  try {
    const response = await fetch("/api/pipelines/groups", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!response.ok) {
      throw await responseToError(response, "Failed to create group");
    }
    const data = await response.json();
    pipelineItems.value = data.items || [];
    pipelineGroups.value = data.groups || [];
  } catch (error) {
    formError.value = error.message;
  }
}

async function submitRenameGroup(payload) {
  const groupNameError = validateGroupName(payload.nextName);
  if (groupNameError) {
    formError.value = groupNameError;
    window.alert(groupNameError);
    return;
  }
  try {
    const response = await fetch(`/api/pipelines/groups/${encodeURIComponent(payload.name)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: payload.nextName }),
    });
    if (!response.ok) {
      throw await responseToError(response, "Failed to rename group");
    }
    const data = await response.json();
    pipelineItems.value = data.items || [];
    pipelineGroups.value = data.groups || [];
    if (editor.groupName === payload.name) {
      editor.groupName = payload.nextName;
    }
  } catch (error) {
    formError.value = error.message;
  }
}

async function deleteGroup(name) {
  if (!window.confirm(`Delete group "${name}"? Pipelines inside it will move to Ungrouped.`)) {
    return;
  }
  try {
    const response = await fetch(`/api/pipelines/groups/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw await responseToError(response, "Failed to delete group");
    }
    const data = await response.json();
    pipelineItems.value = data.items || [];
    pipelineGroups.value = data.groups || [];
    if (editor.groupName === name) {
      editor.groupName = ungroupedLabel;
    }
  } catch (error) {
    formError.value = error.message;
  }
}

async function submitMovePipeline(payload) {
  try {
    const response = await fetch(`/api/pipelines/${encodeURIComponent(payload.item.name)}/group`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ groupName: payload.targetGroup }),
    });
    if (!response.ok) {
      throw await responseToError(response, "Failed to move pipeline");
    }
    const data = await response.json();
    pipelineItems.value = data.items || [];
    pipelineGroups.value = data.groups || [];
    if (editor.name === payload.item.name) {
      editor.groupName = payload.targetGroup;
    }
  } catch (error) {
    formError.value = error.message;
  }
}

async function handleCollectionDeleteItem(payload) {
  const item = payload?.item;
  const permanent = Boolean(payload?.permanent);
  if (!item?.name) {
    return;
  }
  const prompt = permanent
    ? `Delete "${item.displayName}" permanently?`
    : `Move "${item.displayName}" to Deleted?`;
  if (!window.confirm(prompt)) {
    return;
  }
  try {
    const suffix = permanent ? "?permanent=true" : "";
    const response = await fetch(`/api/pipelines/${encodeURIComponent(item.name)}${suffix}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw await responseToError(response, "Failed to delete pipeline");
    }
    const data = await response.json();
    pipelineItems.value = data.items || [];
    pipelineGroups.value = data.groups || [];
    if (editor.name === item.name && permanent) {
      createNewPipeline();
    } else if (editor.name === item.name) {
      editor.groupName = deletedGroupLabel;
    }
  } catch (error) {
    formError.value = error.message;
  }
}

async function saveJsonAsset(kind, payload) {
  formError.value = "";
  formSuccess.value = "";
  if (!ensureDisplayContext()) {
    return;
  }
  let contentToSave = payload;
  let migratedBody = null;
  if (kind === "body") {
    migratedBody = migrateDynamicBodyPlaceholders(payload);
    contentToSave = migratedBody.template;
    postConfigModel.value = mergeDetectedPostConfig(postConfigModel.value, migratedBody);
  }
  assetSavingKey.value = kind;
  try {
    const response = await fetch("/api/pipelines/assets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pipelineName: editor.name || null,
        groupName: editor.groupName,
        displayName: editor.displayName,
        fileName: kind,
        content: contentToSave,
      }),
    });
    if (!response.ok) {
      throw await responseToError(response, "Failed to save JSON asset");
    }
    const data = await response.json();
    const savedContent = data.content || contentToSave;
    if (kind === "header") headerTemplate.value = savedContent;
    if (kind === "body") bodyTemplate.value = savedContent;
    if (kind === "response") responseTemplate.value = savedContent;
    savedAssetTexts[kind] = data.text || stringify(savedContent);
    editor.assetPaths = {
      ...(editor.assetPaths || {}),
      [kind]: data.path || null,
    };
    formSuccess.value = kind === "body" && migratedBody && Object.keys(migratedBody.placeholderPaths).length
      ? "body.json saved; detected request config is not saved yet."
      : `${kind}.json saved`;
  } catch (error) {
    formError.value = error.message;
  } finally {
    assetSavingKey.value = "";
  }
}

async function saveMappingAsset() {
  formError.value = "";
  formSuccess.value = "";
  if (!ensureDisplayContext()) {
    return;
  }
  if (!ensureJsonDependencyReady()) {
    return;
  }
  assetSavingKey.value = "mapping";
  const inferredMapping = inferMappingFromResponseTemplate(responseTemplate.value, mappingModel.value);
  mappingModel.value = inferredMapping;
  const payload = mappingToStorage(inferredMapping);
  try {
    const response = await fetch("/api/pipelines/assets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pipelineName: editor.name || null,
        groupName: editor.groupName,
        displayName: editor.displayName,
        fileName: "mapping",
        content: payload,
      }),
    });
    if (!response.ok) {
      throw await responseToError(response, "Failed to save mapping");
    }
    const data = await response.json();
    mappingModel.value = mappingFromResponseMapping(data.content || payload);
    savedAssetTexts.mapping = data.text || stringify(data.content || payload);
    editor.assetPaths = {
      ...(editor.assetPaths || {}),
      mapping: data.path || null,
    };
    formSuccess.value = "mapping.json saved";
  } catch (error) {
    formError.value = error.message;
  } finally {
    assetSavingKey.value = "";
  }
}

async function savePostConfigAsset() {
  formError.value = "";
  formSuccess.value = "";
  if (!ensureDisplayContext()) {
    return;
  }
  if (!ensureJsonDependencyReady()) {
    return;
  }
  assetSavingKey.value = "post_config";
  try {
    const response = await fetch("/api/pipelines/assets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pipelineName: editor.name || null,
        groupName: editor.groupName,
        displayName: editor.displayName,
        fileName: "post_config",
        content: postConfigModel.value,
      }),
    });
    if (!response.ok) {
      throw await responseToError(response, "Failed to save post config");
    }
    const data = await response.json();
    postConfigModel.value = normalizePostConfig(data.content || postConfigModel.value);
    savedAssetTexts.post_config = data.text || stringify(data.content || postConfigModel.value);
    editor.assetPaths = {
      ...(editor.assetPaths || {}),
      post_config: data.path || null,
    };
    formSuccess.value = "post_config.json saved";
  } catch (error) {
    formError.value = error.message;
  } finally {
    assetSavingKey.value = "";
  }
}

async function savePipeline() {
  formError.value = "";
  formSuccess.value = "";
  const pipelineNameError = validatePipelineName(editor.name);
  if (pipelineNameError) {
    formError.value = pipelineNameError;
    window.alert(pipelineNameError);
    return;
  }
  savingPipeline.value = true;
  try {
    const payload = buildPipelinePayload();
    const response = await fetch("/api/pipelines", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw await responseToError(response, "Failed to save pipeline");
    }
    const data = await response.json();
    const currentImagePath = editor.inputPath;
    resetEditor({ ...data.pipeline, inputPath: currentImagePath }, true);
    activeWorkspaceView.value = "request";
    formSuccess.value = data.message;
    await loadPipelineList();
  } catch (error) {
    formError.value = error.message;
  } finally {
    savingPipeline.value = false;
  }
}

function buildPipelinePayload() {
  const imageFieldPath =
    postConfigModel.value.placeholderPaths?.image_b64 ||
    editor.imageFieldPath ||
    bodyFieldPathOptions.value[0] ||
    "image";
  const inferredMapping = inferMappingFromResponseTemplate(responseTemplate.value, mappingModel.value);
  return {
    ...editor,
    originalName: persistedPipelineName.value || null,
    imageDirectory: null,
    headerTemplate: headerTemplate.value,
    bodyTemplate: bodyTemplate.value,
    responseMapping: mappingToStorage(inferredMapping),
    defaultHeaders: {},
    defaultBody: {},
    defaultExtra: {},
    templateInput: responseTemplate.value,
    postConfig: postConfigModel.value,
    imageFieldPath,
    imageSource: "base64",
    connectTimeout: postConfigModel.value.connectTimeout,
    readTimeout: postConfigModel.value.readTimeout,
  };
}

function mappingToStorage(model) {
  return {
    outputType: "detection",
    collectionPaths: model.collectionPath ? [model.collectionPath] : [],
    itemPath: model.itemPath || null,
    labelPath: model.labelPath || null,
    classIdPath: model.classIdPath || null,
    confPath: model.confPath || null,
    textPath: null,
    bboxMode:
      model.bboxInputMode === "fields"
        ? model.bboxCoordinateType === "xywh"
          ? "xywh_from_paths"
          : "xyxy_from_paths"
        : model.bboxCoordinateType === "xywh"
          ? "xywh_to_xyxy"
          : "passthrough",
    bboxInputMode: model.bboxInputMode,
    bboxCoordinateType: model.bboxCoordinateType,
    bboxIsCenter: false,
    bboxPath: model.bboxPath || null,
    bboxPaths: (model.bboxPaths || []).map((item) => item || null),
    bboxCast: "float",
    names: [],
    plotFields: [
      ...["label", "class_id", "conf"].filter((field) => (model.plotFields || []).includes(field)),
      ...(model.extraFields || [])
        .filter((field) => field.plot && String(field.name || "").trim())
        .map((field) => field.name.trim()),
    ],
    extraFields: (model.extraFields || [])
      .filter((field) => String(field.name || "").trim())
      .map((field) => ({
        name: field.name.trim(),
        path: field.path || null,
        cast: field.cast === "string" ? null : field.cast,
      })),
  };
}

async function loadResponseQueue(path) {
  const inputPath = String(path || "").trim();
  runError.value = "";
  runResult.value = null;
  responseQueue.value = [];
  selectedImagePath.value = "";
  if (!inputPath) {
    return;
  }

  queueLoading.value = true;
  try {
    const params = new URLSearchParams({ path: inputPath });
    const response = await fetch(`/api/images/browse?${params.toString()}`);
    if (!response.ok) {
      throw await responseToError(response, "Failed to list images");
    }
    const data = await response.json();
    responseQueue.value = (data.images || []).map((image) => ({
      name: image.name,
      imagePath: image.path,
      status: "new",
      selected: false,
      sending: false,
      elapsedMs: null,
      parsed: null,
      rawResponse: null,
      error: null,
    }));
    selectedImagePath.value = responseQueue.value[0]?.imagePath || "";
  } catch (error) {
    runError.value = error.message;
  } finally {
    queueLoading.value = false;
  }
}

async function loadSavedRunResults(inputPath, runFolder = "") {
  try {
    const params = new URLSearchParams({ inputPath });
    if (runFolder) {
      params.set("runFolder", runFolder);
    }
    const response = await fetch(
      `/api/pipelines/${encodeURIComponent(editor.name)}/results?${params.toString()}`,
    );
    if (!response.ok) {
      throw await responseToError(response, "Failed to load saved results");
    }
    const data = await response.json();
    applyRunItems(data.items || []);
  } catch (error) {
    runError.value = error.message;
  }
}

function applyRunItems(items) {
  const runItems = items || [];
  const resultMap = new Map(runItems.flatMap((item) => responsePathKeys(item.imagePath).map((key) => [key, item])));
  const hasVisualizationUpdates = runItems.some((item) => item.predCachePath || item.gtCachePath || item.predSavedPath || item.gtSavedPath);
  responseQueue.value = responseQueue.value.map((queueItem) => {
    const result = findRunItemForQueueItem(queueItem, resultMap, runItems);
    if (!result) {
      return queueItem;
    }
    return {
      ...queueItem,
      ...result,
      imagePath: queueItem.imagePath,
      status: result.ok ? "success" : "failed",
      sending: false,
    };
  });
  if (hasVisualizationUpdates) {
    bumpVisualizationRefresh();
  }
}

function findRunItemForQueueItem(queueItem, resultMap, runItems) {
  for (const key of responsePathKeys(queueItem.imagePath)) {
    const result = resultMap.get(key);
    if (result) return result;
  }
  if (runItems.length === 1 && selectedImagePath.value === queueItem.imagePath) {
    return runItems[0];
  }
  return null;
}

function responsePathKeys(path) {
  const normalized = normalizeFilesystemPath(path).toLowerCase();
  if (!normalized) return [];
  const keys = [normalized];
  const base = baseName(normalized).toLowerCase();
  if (base) keys.push("basename:" + base);
  return Array.from(new Set(keys));
}

async function requestPipelineRun(inputPath, signal) {
  const response = await fetch(`/api/pipelines/${encodeURIComponent(editor.name)}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ inputPath, saveResults: true }),
    signal,
  });
  if (!response.ok) {
    throw await responseToError(response, "Failed to run pipeline");
  }
  return response.json();
}

function isAbortError(error) {
  return error?.name === "AbortError";
}

function abortAllImages() {
  if (!runningAll.value) {
    return;
  }
  abortAllRequested.value = true;
  activeBatchController.value?.abort();
}

async function runAllImages() {
  runError.value = "";
  if (!editor.name) {
    runError.value = "Save pipeline before running.";
    return;
  }
  const selectedItems = responseQueue.value.filter((item) => item.selected);
  if (!selectedItems.length) {
    runError.value = "Select at least one image before sending.";
    return;
  }
  runningAll.value = true;
  abortAllRequested.value = false;
  const allItems = [];
  try {
    for (const item of selectedItems) {
      selectedImagePath.value = item.imagePath;
      responseQueue.value = responseQueue.value.map((queueItem) =>
        queueItem.imagePath === item.imagePath ? { ...queueItem, sending: true } : queueItem,
      );
      const controller = new AbortController();
      activeBatchController.value = controller;
      try {
        const data = await requestPipelineRun(item.imagePath, controller.signal);
        allItems.push(...(data.items || []));
        applyRunItems(data.items);
      } catch (error) {
        if (isAbortError(error) && abortAllRequested.value) {
          responseQueue.value = responseQueue.value.map((queueItem) =>
            queueItem.imagePath === item.imagePath
              ? { ...queueItem, status: "abort", sending: false, error: "Aborted" }
              : queueItem,
          );
          break;
        }
        const failedItem = {
          imagePath: item.imagePath,
          ok: false,
          elapsedMs: null,
          error: error.message,
        };
        allItems.push(failedItem);
        applyRunItems([failedItem]);
      } finally {
        responseQueue.value = responseQueue.value.map((queueItem) =>
          queueItem.imagePath === item.imagePath ? { ...queueItem, sending: false } : queueItem,
        );
        if (activeBatchController.value === controller) {
          activeBatchController.value = null;
        }
      }
      if (abortAllRequested.value) {
        break;
      }
    }
    runResult.value = { items: allItems };
    selectedImagePath.value ||= selectedItems[0]?.imagePath || "";
  } finally {
    activeBatchController.value = null;
    abortAllRequested.value = false;
    responseQueue.value = responseQueue.value.map((item) => ({ ...item, sending: false }));
    runningAll.value = false;
  }
}

function setResponseSelected(imagePath, selected) {
  responseQueue.value = responseQueue.value.map((item) =>
    item.imagePath === imagePath ? { ...item, selected } : item,
  );
}

function toggleFilteredSelection(selected) {
  const visiblePaths = new Set(filteredResponseQueue.value.map((item) => item.imagePath));
  responseQueue.value = responseQueue.value.map((item) =>
    visiblePaths.has(item.imagePath) ? { ...item, selected } : item,
  );
}

function startResponseResize(event) {
  if (window.matchMedia("(max-width: 980px)").matches) {
    return;
  }
  event.preventDefault();
  const grid = event.currentTarget.parentElement;
  const bounds = grid.getBoundingClientRect();
  const handleMove = (moveEvent) => {
    const percent = ((moveEvent.clientX - bounds.left) / bounds.width) * 100;
    responseLeftPercent.value = Math.min(76, Math.max(42, percent));
  };
  const stopResize = () => {
    window.removeEventListener("mousemove", handleMove);
    window.removeEventListener("mouseup", stopResize);
    document.body.classList.remove("response-column-resizing");
  };
  document.body.classList.add("response-column-resizing");
  window.addEventListener("mousemove", handleMove);
  window.addEventListener("mouseup", stopResize);
}

async function runSingleImage(item) {
  if (!editor.name || item.sending) {
    return;
  }
  runError.value = "";
  selectedImagePath.value = item.imagePath;
  responseQueue.value = responseQueue.value.map((queueItem) =>
    queueItem.imagePath === item.imagePath ? { ...queueItem, sending: true } : queueItem,
  );
  try {
    const data = await requestPipelineRun(item.imagePath);
    applyRunItems(data.items);
  } catch (error) {
    responseQueue.value = responseQueue.value.map((queueItem) =>
      queueItem.imagePath === item.imagePath
        ? { ...queueItem, status: "failed", sending: false, error: error.message }
        : queueItem,
    );
    runError.value = error.message;
  }
}

function normalizeParsedResult(parsed, mapping) {
  if (!parsed) {
    return null;
  }
  const template = {
    bbox: null,
    conf: null,
    label: null,
    class_id: null,
  };
  for (const field of mapping.extraFields || []) {
    const key = String(field.name || "").trim();
    if (key) {
      template[key] = null;
    }
  }
  const normalizeOne = (item) => {
    const next = { ...template };
    for (const key of Object.keys(next)) {
      next[key] = item?.[key] ?? null;
    }
    return next;
  };
  return Array.isArray(parsed) ? parsed.map(normalizeOne) : normalizeOne(parsed);
}

function ensureDisplayContext() {
  formError.value = "";
  if (!editor.displayName || !editor.groupName) {
    formError.value = "Display Name and Group are required before saving tab files.";
    return false;
  }
  return true;
}

function ensureJsonDependencyReady() {
  formError.value = "";
  if (!jsonDependencyReady.value) {
    formError.value = "Please save Body JSON and Response JSON before editing mapping or request config.";
    activeRequestTab.value = hasJsonContent(savedBodyJson.value) ? "response" : "body";
    return false;
  }
  return true;
}

function hasJsonContent(value) {
  return Boolean(value && typeof value === "object" && !Array.isArray(value) && Object.keys(value).length);
}

function validatePipelineName(value) {
  const name = String(value || "").trim();
  if (name.length < 3 || name.length > 64) {
    return "Pipeline Name must be 3-64 characters.";
  }
  if (!/^[a-z]/.test(name)) {
    return "Pipeline Name must start with a lowercase letter.";
  }
  if (!/^[a-z][a-z0-9_-]{2,63}$/.test(name)) {
    return "Pipeline Name only supports lowercase letters, numbers, _ and -.";
  }
  if (/[_-]$/.test(name)) {
    return "Pipeline Name cannot end with _ or -.";
  }
  if (/__|--|_-|-_/.test(name)) {
    return "Pipeline Name cannot contain consecutive separators.";
  }
  return "";
}

function validateGroupName(value) {
  const error = validatePipelineName(value);
  return error ? error.replaceAll("Pipeline Name", "Group Name") : "";
}

function inferMappingFromResponseTemplate(response, currentMapping) {
  const next = {
    ...currentMapping,
    bboxPaths: [...(currentMapping.bboxPaths || [null, null, null, null])],
    extraFields: [...(currentMapping.extraFields || [])],
  };

  const algoOutputs = response?.data?.algo_outputs;
  const firstObject = Array.isArray(algoOutputs)
    ? algoOutputs.find((item) => Array.isArray(item?.objectinfo))?.objectinfo?.[0]
    : null;
  if (firstObject && typeof firstObject === "object") {
    if (!next.collectionPath || next.collectionPath === "data.outputs") {
      next.collectionPath = "data.algo_outputs";
    }
    next.itemPath ||= "objectinfo";
    next.bboxInputMode = "fields";
    next.bboxCoordinateType = "xyxy";
    next.labelPath ||= "class_name";
    next.classIdPath ||= "class_id";
    next.confPath ||= "confidence";
    next.bboxPaths = [
      next.bboxPaths?.[0] || "rect.x0",
      next.bboxPaths?.[1] || "rect.y0",
      next.bboxPaths?.[2] || "rect.x1",
      next.bboxPaths?.[3] || "rect.y1",
    ];
    return next;
  }

  const outputs = response?.data?.outputs;
  const firstOutput = Array.isArray(outputs) ? outputs[0] : null;
  if (firstOutput && typeof firstOutput === "object") {
    next.collectionPath ||= "data.outputs";
    next.itemPath ||= "";
    if ("x1" in firstOutput && "y1" in firstOutput && "x2" in firstOutput && "y2" in firstOutput) {
      next.bboxInputMode = "fields";
      next.bboxCoordinateType = "xyxy";
      next.bboxPaths = [
        next.bboxPaths?.[0] || "x1",
        next.bboxPaths?.[1] || "y1",
        next.bboxPaths?.[2] || "x2",
        next.bboxPaths?.[3] || "y2",
      ];
    }
    next.labelPath ||= "class";
    next.classIdPath ||= "class_id";
    next.confPath ||= "score";
  }

  return next;
}

function collectResponseMappingPaths(source, mapping) {
  const collectionPaths = collectArrayPaths(source);
  const collectionPath = mapping.collectionPath || collectionPaths[0] || "";
  const collectionItem = firstArrayItem(getValueAtPath(source, collectionPath));
  const itemPaths = collectArrayPaths(collectionItem);
  const itemPath = mapping.itemPath || "";
  const fieldSource = itemPath ? firstArrayItem(getValueAtPath(collectionItem, itemPath)) : collectionItem;
  const fieldPaths = collectObjectPaths(fieldSource);
  return {
    collectionPaths,
    itemPaths,
    fieldPaths,
  };
}

function getValueAtPath(source, path) {
  if (!path) {
    return source;
  }
  return path.split(".").reduce((current, part) => {
    if (current === null || current === undefined) {
      return undefined;
    }
    return current[part];
  }, source);
}

function firstArrayItem(value) {
  return Array.isArray(value) ? value[0] : value;
}

function collectArrayPaths(source, prefix = "") {
  const paths = [];
  if (Array.isArray(source)) {
    if (prefix) {
      paths.push(prefix);
    }
    const first = source[0];
    if (first && typeof first === "object") {
      paths.push(...collectArrayPaths(first, prefix));
    }
  } else if (source && typeof source === "object") {
    for (const [key, value] of Object.entries(source)) {
      const path = prefix ? `${prefix}.${key}` : key;
      paths.push(...collectArrayPaths(value, path));
    }
  }
  return Array.from(new Set(paths));
}

function collectObjectPaths(source, prefix = "") {
  const paths = [];
  if (Array.isArray(source)) {
    const first = source[0];
    if (first && typeof first === "object") {
      paths.push(...collectObjectPaths(first, prefix));
    }
  } else if (source && typeof source === "object") {
    for (const [key, value] of Object.entries(source)) {
      const path = prefix ? `${prefix}.${key}` : key;
      paths.push(path);
      if (value && typeof value === "object") {
        paths.push(...collectObjectPaths(value, path));
      }
    }
  }
  return Array.from(new Set(paths));
}

function parseSavedText(text) {
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return null;
  }
}

function methodClass(method) {
  return String(method || "").toLowerCase();
}

function baseName(path) {
  return String(path || "").split(/[\\/]/).pop();
}

function parentDirectoryPath(path) {
  let normalized = String(path || "").split("\\").join("/");
  while (normalized.length > 1 && normalized.endsWith("/")) {
    normalized = normalized.slice(0, -1);
  }
  const separatorIndex = normalized.lastIndexOf("/");
  if (separatorIndex <= 0) {
    return appConfig.filesystemRoot || normalized;
  }
  return normalized.slice(0, separatorIndex) || appConfig.filesystemRoot || normalized;
}

function imageContentUrl(path) {
  const params = new URLSearchParams({ path });
  if (visualizationRefreshNonce.value) {
    params.set("v", String(visualizationRefreshNonce.value));
  }
  return `/api/images/content?${params.toString()}`;
}

function bumpVisualizationRefresh() {
  visualizationRefreshNonce.value += 1;
}

function hasResponseValue(source, key) {
  return Boolean(source && Object.prototype.hasOwnProperty.call(source, key) && source[key] !== undefined && source[key] !== null);
}

function stringify(value) {
  return JSON.stringify(value ?? null, null, 2);
}

function formatMetric(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(4) : "-";
}

async function responseToError(response, fallback) {
  const data = await response.json().catch(() => ({}));
  const detail = Array.isArray(data.detail)
    ? data.detail.map((item) => item.msg || JSON.stringify(item)).join("; ")
    : data.detail;
  return new Error(detail || `${fallback} (${response.status})`);
}

onMounted(async () => {
  await loadAppConfig();
  rootNode.value.expanded = true;
  await loadChildren(rootNode.value);
  try {
    await loadPipelineList();
  } catch (error) {
    formError.value = error.message;
  }
  resetEditor(null, false);
});

</script>

<style>
.response-send-all .button-icon {
  width: 15px;
  height: 15px;
  flex: 0 0 auto;
  fill: currentColor;
}

.response-send-all.is-running {
  border-color: #dc2626;
  background: #dc2626;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.22);
}

.response-send-all.is-running:hover:not(:disabled) {
  border-color: #b91c1c;
  background: #b91c1c;
  color: #ffffff;
}

.response-list-item.abort {
  border-color: #facc15;
  background: #fffbeb;
}

.response-list-item.abort .response-status-badge {
  background: #fef3c7;
  color: #92400e;
}
</style>
