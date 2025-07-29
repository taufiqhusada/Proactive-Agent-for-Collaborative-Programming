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
                    <div v-if="currentProblem.title[0] != '0'" class="example-header">Subtask {{ index + 1 }}:</div>
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
import { defineComponent, ref, computed, onMounted, watch } from 'vue'

export default defineComponent({
    name: 'ProblemDescription',
    emits: ['problem-changed', 'boilerplate-changed'],
    props: {
        selectedProblem: {
            type: Number,
            default: 0
        }
    },
    setup(props, { emit }) {
        const selectedProblem = ref(props.selectedProblem)

        const problems = ref([
            {
                title: "0. First Repeated Number",
                difficulty: "Easy",
                description: `
                    <p>Given a list of integers, return the first number that appears more than once.</p>
                    <p>If no number repeats, return <code>None</code>.</p>
                    <p>This is an introductory problem to get familiar with the coding environment.</p>
                `,
                examples: [
                    {
                        input: "nums = [2, 5, 3, 2, 8, 7]",
                        output: "2",
                        explanation: "2 is the first number that appears more than once."
                    },
                    {
                        input: "nums = [1, 2, 3, 4, 5]",
                        output: "None",
                        explanation: "No number repeats in the list."
                    },
                    {
                        input: "nums = [5, 3, 4, 3, 5, 6]",
                        output: "3",
                        explanation: "Both 3 and 5 repeat, but 3 appears twice first."
                    }
                ],
                constraints: [
                    "1 ≤ nums.length ≤ 10⁴",
                    "-10⁶ ≤ nums[i] ≤ 10⁶"
                ]
            },
            {
                title: "1. Gift Card Purchase Assistant",
                difficulty: "Easy",
                description: `
                    <p><strong>Scenario:</strong> A user has a gift card with a fixed value (e.g., $100) and wants to buy two items from their shopping cart whose prices add up exactly to the gift card value.</p>
                    <p>Implement a Gift Card Purchase Assistant that helps the user make the best use of their gift card.</p>
                    <ul>
                        <li><strong>Subtask 1:</strong> Given the user wants to buy one item, suggest which other item they should buy (by index) to use the gift card exactly.</li>
                        <li><strong>Subtask 2:</strong> Return all pairs of item indices whose prices add up exactly to the gift card value.</li>
                        <li><strong>Subtask 3:</strong> Find the pair (by indices) that includes the highest-priced item possible. </li>
                    </ul>
                `,
                examples: [
                    {
                        input: "prices =  [40, 60, 20, 80, 90], gift_card = 100, chosen_index = 2",
                        output: "0",
                        explanation: "If user chooses item at index 1 (price 60), suggest index 0 (price 40) to use the gift card."
                    },
                    {
                        input: "prices = [40, 60, 20, 80, 90], gift_card = 100",
                        output: "[[0,1],[2,3]]",
                        explanation: "Items at indices [0,1] and [2,3] both sum to 100."
                    },
                    {
                        input: "prices = [40, 60, 20, 80, 90], gift_card = 100",
                        output: "[2,3]",
                        explanation: "[2,3] is chosen because it includes 80, the highest single item in any valid pair summing to 100. No pair can be form with 90, so we chose to include 80 instead."
                    }
                ],
                constraints: [
                    "2 ≤ prices.length ≤ 10⁴",
                    "1 ≤ prices[i] ≤ 10⁴",
                    "All prices are positive integers.",
                ]
            },
            {
                title: "2. Step Tracker Insight",
                difficulty: "Medium",
                description: `
                    <p><strong>Scenario:</strong> A fitness tracking app that tracks user daily step counts in an array.</p>
                    <p>Implement a Step Tracker Insight program that provides the following informations on the user's daily step data.</p>
                    <ul>
                        <li><strong>Subtask 1 - Daily Average:</strong> Calculate the overall average steps per day across all recorded days.</li>
                        <li><strong>Subtask 2 - Best K-Day Streak Average:</strong> Find the highest average step count within any k consecutive days.</li>
                        <li><strong>Subtask 3 - Goal Achievement Streak:</strong> Find the shortest consecutive days needed to reach or exceed a target step sum.</li>
                    </ul>
                `,
                examples: [
                    {
                        input: "steps = [8000, 12000, 10000, 6000, 15000, 9000, 11000]",
                        output: "10142.86",
                        explanation: "Sum of all steps (71000) divided by number of days (7)."
                    },
                    {
                        input: "steps = [8000, 12000, 10000, 6000, 15000, 9000, 11000], k = 3",
                        output: "11666.67",
                        explanation: "Best 3-day average is from days with steps [15000, 9000, 11000] gives 11666.67."
                    },
                    {
                        input: "steps = [8000, 12000, 10000, 6000, 15000, 9000, 11000], target = 31000",
                        output: "3",
                        explanation: "Shortest subarray with sum ≥ 31000 is [10000, 6000, 15000] with length 3 and sum 31000."
                    }
                ],
                constraints: [
                    "1 ≤ steps.length ≤ 10⁴",
                    "1 ≤ steps[i] ≤ 10⁵",
                    "1 ≤ k ≤ steps.length",
                    "1 ≤ target ≤ 10⁵"
                ]
            },
            {
                title: "3. Meeting Room Scheduler",
                difficulty: "Medium",
                description: `
                    <p><strong>Scenario:</strong> A meeting room booking system that manages time slots for conference rooms. Each booking is represented as an interval [start_time, end_time].</p>
                    <p>Implement a Meeting Room Scheduler that optimizes room usage by merging overlapping bookings.</p>
                    <ul>
                        <li><strong>Subtask 1 - Sort Bookings:</strong> Sort all meeting intervals by their start time.</li>
                        <li><strong>Subtask 2 - Merge Overlapping:</strong> Merge all overlapping or adjacent meeting intervals.</li>
                        <li><strong>Subtask 3 - Add New Meeting:</strong> Insert a new meeting interval and merge with existing bookings as needed.</li>
                    </ul>
                `,
                examples: [
                    {
                        input: "intervals = [[1,3],[9,14],[2,5],[4,7],[15,18]]",
                        output: "[[1,3],[2,5],[4,7],[9,14],[15,18]]",
                        explanation: "Intervals sorted by start time."
                    },
                    {
                        input: "intervals = [[1,3],[9,14],[2,5],[4,7],[15,18]]",
                        output: "[[1,7],[9,14],[15,18]]",
                        explanation: "After merging: [1,3], [2,5], and [4,7] all overlap and merge to [1,7]. [9,14] and [15,18] remain separate."
                    },
                    {
                        input: "intervals = [[1,3],[9,14],[2,5],[4,7],[15,18]], new_interval = [8,16]",
                        output: "[[1,7],[8,18]]",
                        explanation: "Added [8,16], which bridges [9,14] and [15,18] to create [8,18], while [1,7] remains separate."
                    }
                ],
                constraints: [
                    "0 ≤ intervals.length ≤ 10⁴",
                    "intervals[i].length == 2",
                    "0 ≤ start_i ≤ end_i ≤ 10⁴",
                    "0 ≤ new_interval[0] ≤ new_interval[1] ≤ 10⁴"
                ]
            }
        ])

        // Boilerplate code for Gift Card Purchase Assistant (Python)
        const giftCardBoilerplate = `prices = [40, 60, 20, 80, 90]
gift_card = 100

def suggest_pair(prices, gift_card, chosen_index):
  # Find the index of an item that pairs with the chosen item to use the gift card exactly

  return None

def find_all_pairs(prices, gift_card):
  # Return all pairs of item indices whose prices add up exactly to the gift card value

  return []

def find_highest_pair(prices, gift_card):
  # Find the pair that includes the highest-priced item possible
    
  return []

# Example usage:
print(suggest_pair(prices, gift_card, 1))
print(find_all_pairs(prices, gift_card))
print(find_highest_pair(prices, gift_card))
                `;

        // Boilerplate code for Step Tracker Insight (Python)
        const stepTrackerBoilerplate = `steps = [8000, 12000, 10000, 6000, 15000, 9000, 11000]
k = 3
target = 30000

def daily_average(steps):
  # Calculate the overall average steps per day across all recorded days

  return 0.0

def best_k_day_streak(steps, k):
  # Find the highest average step count within any k consecutive days

  return 0.0

def shortest_perfect_goal_streak(steps, target):
  # Find the shortest consecutive days needed to reach or exceed a target step sum

  return 0

# Example usage:
print(f"Daily average: {daily_average(steps)}")
print(f"Best {k}-day streak average: {best_k_day_streak(steps, k)}")
print(f"Shortest streak to reach {target}: {shortest_perfect_goal_streak(steps, target)}")
                `;

        // Boilerplate code for Meeting Room Scheduler (Python)
        const meetingRoomBoilerplate = `intervals = [[1,3],[9,14],[2,5],[4,7],[15,18]]
new_interval = [8,16]

def sort_intervals(intervals):
  # Sort all meeting intervals by their start time

  return []

def merge_intervals(intervals):
  # Merge all overlapping or adjacent meeting intervals

  return []

def insert_and_merge(intervals, new_interval):
  # Insert a new meeting interval and merge with existing bookings as needed

  return []

# Example usage:
print(f"Sorted intervals: {sort_intervals(intervals)}")
print(f"Merged intervals: {merge_intervals(intervals)}")
print(f"After inserting {new_interval}: {insert_and_merge(intervals, new_interval)}")
                `;

        // Boilerplate code for First Repeated Number (Python)
        const firstRepeatedBoilerplate = `nums = [2, 5, 3, 2, 8, 7]

def first_repeated_number(nums):
  # Return the first number that appears more than once in the list
    
  return None

# Example usage:
print(first_repeated_number(nums))
                `;

        const problemBoilerplates = [
            firstRepeatedBoilerplate, // First Repeated Number
            giftCardBoilerplate, // Gift Card Purchase Assistant
            stepTrackerBoilerplate, // Step Tracker Insight
            meetingRoomBoilerplate // Meeting Room Scheduler
        ];

        const currentProblem = computed(() => problems.value[selectedProblem.value])

        const onProblemChange = () => {
            emit('problem-changed', {
                problemIndex: selectedProblem.value,
                problem: currentProblem.value
            })
        }

        // Emit initial problem on mount
        onMounted(() => {
            onProblemChange()
        })

        watch(() => props.selectedProblem, (newVal) => {
            selectedProblem.value = newVal
        })

        watch(selectedProblem, (newIndex) => {
            if (problemBoilerplates[newIndex]) {
                emit('boilerplate-changed', problemBoilerplates[newIndex]);
            }
            emit('problem-changed', {
                problemIndex: newIndex,
                problem: problems.value[newIndex]
            })
        });

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
    max-height: 650px;
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
