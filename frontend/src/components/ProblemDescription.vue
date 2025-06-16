<template>
    <div class="problem-description">
        <div class="problem-header">
            <div class="problem-title">
                <!-- <span class="problem-icon">🎯</span> -->
                <h5>Problem Description</h5>
            </div>
            <div class="problem-selector">
                <select v-model="selectedProblem" @change="onProblemChange" class="problem-select">
                    <option v-for="(problem, index) in problems" :key="index" :value="index">
                        {{ problem.title }}
                    </option>
                </select>
            </div>
        </div>

        <div class="problem-content">
            <div class="problem-statement">
                <!-- <div class="difficulty-badge" :class="currentProblem.difficulty.toLowerCase()">
                    {{ currentProblem.difficulty }}
                </div> -->
                <h6 class="problem-name">{{ currentProblem.title }}</h6>
                <div class="problem-description-text" v-html="currentProblem.description"></div>
            </div>

            <div v-if="currentProblem.examples && currentProblem.examples.length > 0" class="examples-section">
                <h6>Examples:</h6>
                <div v-for="(example, index) in currentProblem.examples" :key="index" class="example">
                    <div class="example-header">Example {{ index + 1 }}:</div>
                    <div class="example-content">
                        <div class="example-input">
                            <strong>Input:</strong> <code>{{ example.input }}</code>
                        </div>
                        <div class="example-output">
                            <strong>Output:</strong> <code>{{ example.output }}</code>
                        </div>
                        <div v-if="example.explanation" class="example-explanation">
                            <strong>Explanation:</strong> {{ example.explanation }}
                        </div>
                    </div>
                </div>
            </div>

            <div v-if="currentProblem.constraints" class="constraints-section">
                <h6>Constraints:</h6>
                <ul class="constraints-list">
                    <li v-for="(constraint, index) in currentProblem.constraints" :key="index">
                        {{ constraint }}
                    </li>
                </ul>
            </div>
        </div>
    </div>
</template>

<script>
import { defineComponent, ref, computed } from 'vue'

export default defineComponent({
    name: 'ProblemDescription',
    emits: ['problem-changed'],
    setup(_, { emit }) {
        const selectedProblem = ref(0)

        const problems = ref([
            {
                title: "Two Sum",
                difficulty: "Easy",
                description: `
                    <p>Given an array of integers <code>nums</code> and an integer <code>target</code>, return <em>indices of the two numbers such that they add up to <code>target</code></em>.</p>
                    <p>You may assume that each input would have <strong>exactly one solution</strong>, and you may not use the same element twice.</p>
                    <p>You can return the answer in any order.</p>
                `,
                examples: [
                    {
                        input: "nums = [2,7,11,15], target = 9",
                        output: "[0,1]",
                        explanation: "Because nums[0] + nums[1] == 9, we return [0, 1]."
                    },
                    {
                        input: "nums = [3,2,4], target = 6",
                        output: "[1,2]",
                        explanation: ""
                    },
                    {
                        input: "nums = [3,3], target = 6",
                        output: "[0,1]",
                        explanation: ""
                    }
                ],
                constraints: [
                    "2 ≤ nums.length ≤ 10⁴",
                    "-10⁹ ≤ nums[i] ≤ 10⁹",
                    "-10⁹ ≤ target ≤ 10⁹",
                    "Only one valid answer exists."
                ]
            },
            {
                title: "Add Two Numbers",
                difficulty: "Medium",
                description: `
                    <p>You are given two <strong>non-empty</strong> linked lists representing two non-negative integers. The digits are stored in <strong>reverse order</strong>, and each of their nodes contains a single digit. Add the two numbers and return the sum as a linked list.</p>
                    <p>You may assume the two numbers do not contain any leading zero, except the number 0 itself.</p>
                `,
                examples: [
                    {
                        input: "l1 = [2,4,3], l2 = [5,6,4]",
                        output: "[7,0,8]",
                        explanation: "342 + 465 = 807."
                    },
                    {
                        input: "l1 = [0], l2 = [0]",
                        output: "[0]",
                        explanation: ""
                    },
                    {
                        input: "l1 = [9,9,9,9,9,9,9], l2 = [9,9,9,9]",
                        output: "[8,9,9,9,0,0,0,1]",
                        explanation: ""
                    }
                ],
                constraints: [
                    "The number of nodes in each linked list is in the range [1, 100].",
                    "0 ≤ Node.val ≤ 9",
                    "It is guaranteed that the list represents a number that does not have leading zeros."
                ]
            },
            {
                title: "Longest Substring Without Repeating Characters",
                difficulty: "Medium",
                description: `
                    <p>Given a string <code>s</code>, find the length of the <strong>longest substring</strong> without repeating characters.</p>
                `,
                examples: [
                    {
                        input: 's = "abcabcbb"',
                        output: "3",
                        explanation: 'The answer is "abc", with the length of 3.'
                    },
                    {
                        input: 's = "bbbbb"',
                        output: "1",
                        explanation: 'The answer is "b", with the length of 1.'
                    },
                    {
                        input: 's = "pwwkew"',
                        output: "3",
                        explanation: 'The answer is "wke", with the length of 3.'
                    }
                ],
                constraints: [
                    "0 ≤ s.length ≤ 5 × 10⁴",
                    "s consists of English letters, digits, symbols and spaces."
                ]
            },
            {
                title: "Valid Parentheses",
                difficulty: "Easy",
                description: `
                    <p>Given a string <code>s</code> containing just the characters <code>'('</code>, <code>')'</code>, <code>'{'</code>, <code>'}'</code>, <code>'['</code> and <code>']'</code>, determine if the input string is valid.</p>
                    <p>An input string is valid if:</p>
                    <ol>
                        <li>Open brackets must be closed by the same type of brackets.</li>
                        <li>Open brackets must be closed in the correct order.</li>
                        <li>Every close bracket has a corresponding open bracket of the same type.</li>
                    </ol>
                `,
                examples: [
                    {
                        input: 's = "()"',
                        output: "true",
                        explanation: ""
                    },
                    {
                        input: 's = "()[]{}"',
                        output: "true",
                        explanation: ""
                    },
                    {
                        input: 's = "(]"',
                        output: "false",
                        explanation: ""
                    }
                ],
                constraints: [
                    "1 ≤ s.length ≤ 10⁴",
                    "s consists of parentheses only '()[]{}'."
                ]
            }
        ])

        const currentProblem = computed(() => problems.value[selectedProblem.value])

        const onProblemChange = () => {
            emit('problem-changed', {
                problemIndex: selectedProblem.value,
                problem: currentProblem.value
            })
        }

        return {
            selectedProblem,
            problems,
            currentProblem,
            onProblemChange
        }
    }
})
</script>

<style scoped>
.problem-description {
    background: white;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    overflow: hidden;
}

.problem-header {
    padding: 1rem 1.5rem;
    background: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
}

.problem-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 1;
}

.problem-title h5 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: #2d3748;
}

.problem-icon {
    font-size: 1.1rem;
}

.problem-selector {
    display: flex;
    align-items: center;
    flex-shrink: 0;
}

.problem-select {
    padding: 0.5rem 0.75rem;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    background: white;
    color: #2d3748;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    min-width: 160px;
    max-width: 180px;
}

.problem-select:hover {
    border-color: #4f46e5;
}

.problem-select:focus {
    outline: none;
    border-color: #4f46e5;
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.problem-content {
    padding: 1.5rem;
    max-height: 680px;
    overflow-y: auto;
}

.problem-statement {
    margin-bottom: 1.5rem;
}

.difficulty-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.75rem;
}

.difficulty-badge.easy {
    background: rgba(34, 197, 94, 0.1);
    color: #15803d;
}

.difficulty-badge.medium {
    background: rgba(251, 191, 36, 0.1);
    color: #d97706;
}

.difficulty-badge.hard {
    background: rgba(239, 68, 68, 0.1);
    color: #dc2626;
}

.problem-name {
    margin: 0 0 1rem 0;
    font-size: 1.125rem;
    font-weight: 600;
    color: #1f2937;
}

.problem-description-text {
    color: #4b5563;
    line-height: 1.6;
    margin-bottom: 1rem;
}

.problem-description-text :deep(p) {
    margin-bottom: 0.75rem;
}

.problem-description-text :deep(code) {
    background: #f3f4f6;
    padding: 0.125rem 0.25rem;
    border-radius: 3px;
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 0.875em;
    color: #d97706;
}

.examples-section, .constraints-section {
    margin-bottom: 1.5rem;
}

.examples-section h6, .constraints-section h6 {
    margin: 0 0 0.75rem 0;
    font-size: 1rem;
    font-weight: 600;
    color: #1f2937;
}

.example {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.75rem;
}

.example-header {
    font-weight: 600;
    color: #4b5563;
    margin-bottom: 0.5rem;
}

.example-content > div {
    margin-bottom: 0.5rem;
}

.example-content > div:last-child {
    margin-bottom: 0;
}

.example-input, .example-output, .example-explanation {
    font-size: 0.875rem;
    line-height: 1.5;
}

.example-input code, .example-output code {
    background: #e5e7eb;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-family: 'Monaco', 'Menlo', monospace;
    color: #1f2937;
}

.constraints-list {
    margin: 0;
    padding-left: 1.25rem;
    color: #4b5563;
}

.constraints-list li {
    margin-bottom: 0.25rem;
    font-size: 0.875rem;
    line-height: 1.5;
}

.constraints-list li code {
    background: #f3f4f6;
    padding: 0.125rem 0.25rem;
    border-radius: 3px;
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 0.875em;
    color: #d97706;
}

/* Scrollbar styling */
.problem-content::-webkit-scrollbar {
    width: 4px;
}

.problem-content::-webkit-scrollbar-track {
    background: #f1f5f9;
}

.problem-content::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 2px;
}

.problem-content::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
}
</style>
