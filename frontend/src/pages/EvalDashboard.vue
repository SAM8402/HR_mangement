<template>
  <div class="eval-dashboard">
    <div class="header">
      <h1>AI System Evaluation</h1>
      <button class="btn-refresh" @click="fetchMetrics" :disabled="loading">
        <span v-if="loading">&#8635; Loading...</span>
        <span v-else>&#8635; Refresh Metrics</span>
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading && !metrics" class="loading-state">
      <div class="spinner"></div>
      <p>Fetching AI system performance logs...</p>
    </div>

    <!-- Metrics Cards -->
    <div v-else-if="metrics" class="metrics-grid">
      <div class="metric-card glass">
        <div class="metric-icon">&#128172;</div>
        <div class="metric-content">
          <h3>Total Audited Queries</h3>
          <p class="value">{{ metrics.total_count }}</p>
        </div>
      </div>

      <div class="metric-card glass positive">
        <div class="metric-icon">&#128077;</div>
        <div class="metric-content">
          <h3>Helpful Responses</h3>
          <p class="value">{{ metrics.positive_count }}</p>
        </div>
      </div>

      <div class="metric-card glass negative">
        <div class="metric-icon">&#128078;</div>
        <div class="metric-content">
          <h3>Unhelpful Responses</h3>
          <p class="value">{{ metrics.negative_count }}</p>
        </div>
      </div>

      <div class="metric-card glass satisfaction">
        <div class="metric-icon">&#9733;</div>
        <div class="metric-content">
          <h3>Satisfaction Rate</h3>
          <p class="value">{{ metrics.satisfaction_rate }}%</p>
        </div>
      </div>
    </div>

    <!-- Auditing Logs Table -->
    <div v-if="metrics" class="logs-section glass">
      <h2>Recent Downvoted Queries (Auditing)</h2>
      <div class="table-container">
        <table v-if="metrics.recent_negatives && metrics.recent_negatives.length > 0">
          <thead>
            <tr>
              <th>Date</th>
              <th>User Query</th>
              <th>System Response</th>
              <th>User Explanation / Feedback</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in metrics.recent_negatives" :key="log.id">
              <td class="date-cell">{{ formatDate(log.created_at) }}</td>
              <td class="query-cell">{{ log.query }}</td>
              <td class="response-cell">{{ log.response }}</td>
              <td class="feedback-cell">{{ log.feedback_text || 'No comment left' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-logs">
          <p>🎉 Excellent! No unhelpful responses logged in this period.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getEvaluationMetrics } from '../api/chat.js'

const metrics = ref(null)
const loading = ref(false)

async function fetchMetrics() {
  loading.value = true
  try {
    const res = await getEvaluationMetrics()
    metrics.value = res.data
  } catch (err) {
    console.error('Failed to load metrics', err)
  } finally {
    loading.value = false
  }
}

function formatDate(dateStr) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  fetchMetrics()
})
</script>

<style scoped>
.eval-dashboard {
  max-width: 1000px;
  margin: 0 auto;
  padding-bottom: 40px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header h1 {
  font-size: 1.6rem;
  color: #1e293b;
  font-weight: 700;
}

.btn-refresh {
  padding: 8px 16px;
  background: white;
  border: 1px solid #cbd5e1;
  color: #475569;
  font-weight: 500;
  border-radius: 8px;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.btn-refresh:hover:not(:disabled) {
  border-color: #2563eb;
  color: #2563eb;
  background: #f8fafc;
}

.loading-state {
  text-align: center;
  padding: 60px;
  color: #64748b;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e2e8f0;
  border-top-color: #2563eb;
  border-radius: 50%;
  margin: 0 auto 16px auto;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.glass {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.metric-card {
  display: flex;
  align-items: center;
  padding: 20px;
  gap: 16px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
}

.metric-icon {
  font-size: 2rem;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: #f1f5f9;
}

.positive .metric-icon {
  background: #ecfdf5;
  color: #059669;
}

.negative .metric-icon {
  background: #fef2f2;
  color: #dc2626;
}

.satisfaction .metric-icon {
  background: #fffbeb;
  color: #d97706;
}

.metric-content h3 {
  font-size: 0.8rem;
  color: #64748b;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

.metric-content .value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1e293b;
}

.logs-section {
  padding: 24px;
}

.logs-section h2 {
  font-size: 1.1rem;
  color: #1e293b;
  margin-bottom: 16px;
  font-weight: 600;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.85rem;
}

th {
  padding: 12px 16px;
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  border-bottom: 1px solid #e2e8f0;
}

td {
  padding: 14px 16px;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: top;
  color: #334155;
  line-height: 1.4;
}

tr:hover td {
  background: #f8fafc;
}

.date-cell {
  white-space: nowrap;
  color: #64748b;
  font-weight: 500;
}

.query-cell {
  font-weight: 500;
  max-width: 200px;
}

.response-cell {
  color: #475569;
  max-width: 300px;
}

.feedback-cell {
  font-style: italic;
  color: #dc2626;
}

.empty-logs {
  text-align: center;
  padding: 40px;
  color: #059669;
  font-weight: 500;
}
</style>
