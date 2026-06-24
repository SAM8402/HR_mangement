<template>
  <div :class="['message-row', message.role === 'user' ? 'user' : 'assistant']">
    <div :class="['message-bubble', message.role === 'user' ? 'user' : 'assistant']">
      <div class="message-text">{{ message.content }}</div>
      
      <!-- Citations Section -->
      <div v-if="message.role === 'assistant' && message.citations && message.citations.length > 0" class="citations-section">
        <span class="citations-title">Sources:</span>
        <div class="citations-list">
          <div 
            v-for="cite in message.citations" 
            :key="cite.id" 
            class="citation-tag"
            :title="cite.source"
          >
            [{{ cite.id }}] {{ cite.title || cite.source }}
          </div>
        </div>
      </div>

      <div class="bubble-footer">
        <div v-if="message.timestamp" class="message-time">
          {{ formatTime(message.timestamp) }}
        </div>

        <!-- Feedback Buttons (Assistant Only) -->
        <div v-if="message.role === 'assistant'" class="feedback-actions">
          <button 
            :class="['feedback-btn', { active: feedbackState === 'up' }]" 
            @click="handleFeedback(true)"
            :disabled="submittingFeedback"
            title="Helpful"
          >
            &#128077;
          </button>
          <button 
            :class="['feedback-btn', { active: feedbackState === 'down' }]" 
            @click="handleFeedback(false)"
            :disabled="submittingFeedback"
            title="Unhelpful"
          >
            &#128078;
          </button>
        </div>
      </div>

      <!-- Feedback Text Input (Visible only if downvoted and not submitted yet) -->
      <div v-if="showCommentInput" class="feedback-comment-box">
        <textarea 
          v-model="commentText" 
          placeholder="What was wrong? (optional)" 
          rows="2"
          class="feedback-textarea"
        ></textarea>
        <div class="comment-actions">
          <button class="btn-submit-comment" @click="submitComment" :disabled="submittingFeedback">Submit</button>
          <button class="btn-cancel-comment" @click="showCommentInput = false">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { submitFeedback } from '../../api/chat.js'

const props = defineProps({
  message: { type: Object, required: true }
})

const feedbackState = ref(props.message.feedbackSubmitted) // 'up' or 'down' or null
const showCommentInput = ref(false)
const commentText = ref('')
const submittingFeedback = ref(false)

function formatTime(ts) {
  const date = new Date(ts)
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}

async function handleFeedback(rating) {
  if (submittingFeedback.value) return
  
  submittingFeedback.value = true
  const state = rating ? 'up' : 'down'
  feedbackState.value = state

  if (!rating) {
    showCommentInput.value = true
    submittingFeedback.value = false
    return
  }

  // If thumbs-up, send feedback immediately
  try {
    await submitFeedback({
      query: '', // Will be matched by user session in backend, or leave empty/fallback
      response: props.message.content,
      rating: true,
      feedback_text: 'Helpful response'
    })
    props.message.feedbackSubmitted = 'up'
  } catch (err) {
    console.error('Failed to submit feedback', err)
  } finally {
    submittingFeedback.value = false
  }
}

async function submitComment() {
  submittingFeedback.value = true
  try {
    await submitFeedback({
      query: '',
      response: props.message.content,
      rating: false,
      feedback_text: commentText.value
    })
    props.message.feedbackSubmitted = 'down'
    showCommentInput.value = false
  } catch (err) {
    console.error('Failed to submit feedback comment', err)
  } finally {
    submittingFeedback.value = false
  }
}
</script>

<style scoped>
.message-row {
  display: flex;
  margin-bottom: 8px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 75%;
  padding: 12px 14px;
  border-radius: 12px;
  font-size: 0.9rem;
  line-height: 1.5;
  word-break: break-word;
  position: relative;
}

.message-bubble.user {
  background: #2563eb;
  color: white;
  border-bottom-right-radius: 4px;
}

.message-bubble.assistant {
  background: #f1f5f9;
  color: #1e293b;
  border-bottom-left-radius: 4px;
}

.message-text {
  white-space: pre-wrap;
}

.citations-section {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed #cbd5e1;
}

.citations-title {
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
  display: block;
  margin-bottom: 4px;
}

.citations-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.citation-tag {
  background: #e2e8f0;
  color: #475569;
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 6px;
  font-weight: 500;
  cursor: help;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bubble-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
  font-size: 0.7rem;
  opacity: 0.8;
}

.message-time {
  opacity: 0.6;
}

.feedback-actions {
  display: flex;
  gap: 6px;
}

.feedback-btn {
  background: none;
  border: none;
  font-size: 0.85rem;
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  opacity: 0.4;
  transition: opacity 0.2s, transform 0.1s;
}

.feedback-btn:hover {
  opacity: 0.8;
  transform: scale(1.1);
}

.feedback-btn.active {
  opacity: 1;
}

.feedback-btn.active[title="Helpful"] {
  filter: drop-shadow(0 0 2px #059669);
}

.feedback-btn.active[title="Unhelpful"] {
  filter: drop-shadow(0 0 2px #dc2626);
}

.feedback-comment-box {
  margin-top: 8px;
  padding: 8px;
  background: white;
  border-radius: 8px;
  border: 1px solid #cbd5e1;
}

.feedback-textarea {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 0.75rem;
  resize: none;
  outline: none;
}

.feedback-textarea:focus {
  border-color: #2563eb;
}

.comment-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 4px;
}

.btn-submit-comment,
.btn-cancel-comment {
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.btn-submit-comment {
  background: #2563eb;
  color: white;
}

.btn-cancel-comment {
  background: #f1f5f9;
  color: #475569;
}
</style>
