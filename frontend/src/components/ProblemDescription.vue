<template>
    <div class="problem-description">
        <div class="problem-header">
            <div class="problem-title">
                <!-- <span class="problem-icon">🎯</span> -->
                <h5>Problem Description</h5>
            </div>
            <div class="problem-selector" style="position: relative;">
                <select v-model="selectedProblem" @change="onProblemChange" class="problem-select">
                    <option v-for="(problem, index) in problems" :key="index" :value="index">
                        {{ problem.title }}
                    </option>
                </select>
                <div v-if="showResetPopup" class="reset-popup">
                    <span>Reset code to template for this problem?</span>
                    <div class="reset-popup-buttons">
                        <button @click="confirmReset(true)">Yes</button>
                        <button @click="confirmReset(false)">No</button>
                    </div>
                </div>
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
    emits: ['problem-changed', 'boilerplate-changed', 'reset-confirmed'],
    props: {
        selectedProblem: {
            type: Number,
            default: 0
        },
        language: {
            type: String,
            default: 'python'
        }
    },
    setup(props, { emit }) {
        const selectedProblem = ref(props.selectedProblem)

        const problems = ref([
            {
                title: "0. First Repeated Number",
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
                description: `
                    <p><strong>Scenario:</strong> A user has a gift card with a fixed value (e.g., $100) and wants to buy two items from their shopping cart whose prices add up exactly to the gift card value.</p>
                    <p>Implement a Gift Card Purchase Assistant that helps the user make the best use of their gift card.</p>
                    <ul>
                        <li><strong>Subtask 1:</strong> Given a chosen item index, find another item whose price equals the remaining gift card balance (gift_card_value - chosen_item_price).</li>
                        <li><strong>Subtask 2:</strong> Return all pairs of item indices whose prices add up exactly to the gift card value.</li>
                        <li><strong>Subtask 3:</strong> Find the pair (by indices) that includes the highest possible individual item price among all valid pairs that sum to the gift card value.</li>
                    </ul>
                `,
                examples: [
                    {
                        input: "prices =  [40, 60, 20, 80, 90], gift_card_value = 100, chosen_index = 1",
                        output: "0",
                        explanation: "Item at index 1 costs $60. Remaining balance: $100 - $60 = $40. Find item with price $40, which is at index 0."
                    },
                    {
                        input: "prices = [40, 60, 20, 80, 90], gift_card_value = 100",
                        output: "[[0,1],[2,3]]",
                        explanation: "Items at indices [0,1] and [2,3] both sum to 100."
                    },
                    {
                        input: "prices = [40, 60, 20, 80, 90], gift_card_value = 100",
                        output: "[2,3]",
                        explanation: "[2,3] is chosen because it includes price 80 (at index 3), which is the highest individual item price among all valid pairs. Valid pairs: [0,1] has max price 60, [2,3] has max price 80, so [2,3] wins."
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
                description: `
                    <p><strong>Scenario:</strong> A fitness tracking app that tracks user daily step counts in an array.</p>
                    <p>Implement a Step Tracker Insight program that provides the following informations on the user's daily step data.</p>
                    <ul>
                        <li><strong>Subtask 1 - Daily Average:</strong> Calculate the overall average steps per day across all recorded days.</li>
                        <li><strong>Subtask 2 - Best K-Day Streak Average:</strong> Find the highest average step count within any k consecutive days.</li>
                        <li><strong>Subtask 3 - Shortest Target Subarray:</strong> Find the shortest contiguous subarray (consecutive days) where the total number of steps is at least a given target.</li>
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
                        input: "steps = [8000, 12000, 10000, 6000, 15000, 9000, 11000], target = 24000",
                        output: "2",
                        explanation: "Shortest subarray with sum ≥ 24000: [15000, 9000] = 24000 with length 2. Other subarrays like [8000, 12000, 10000] = 30000 have length 3, which is longer."
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
                description: `
                    <p><strong>Scenario:</strong> A meeting room booking system that manages time slots for conference rooms. Each booking is represented as an interval [start_time, end_time].</p>
                    <p>Implement a Meeting Room Analyzer that provides insights on meeting schedules and helps optimize room usage.</p>
                    <ul>
                        <li><strong>Subtask 1 - Longest Meeting:</strong> Find the meeting with the longest duration.</li>
                        <li><strong>Subtask 2 - Detect Conflicts:</strong> Identify all pairs of meetings that have overlapping time intervals.</li>
                        <li><strong>Subtask 3 - Merge Overlapping:</strong> Merge all overlapping or adjacent meeting intervals into a single interval.</li>
                    </ul>
                `,
                examples: [
                    {
                        input: "intervals = [[1,4],[6,10],[2,5],[8,12]]",
                        output: "[6,10]",
                        explanation: "Meeting [6,10] has the longest duration of 4 time units."
                    },
                    {
                        input: "intervals = [[1,4],[6,10],[2,5],[8,12]]",
                        output: "[[1,4],[2,5]], [[6,10],[8,12]]",
                        explanation: "Two overlapping pairs: [1,4] overlaps with [2,5], and [6,10] overlaps with [8,12]."
                    },
                    {
                        input: "intervals = [[1,4],[6,10],[2,5],[8,12]]",
                        output: "[[1,5],[6,12]]",
                        explanation: "After merging: [1,4] and [2,5] merge to [1,5], and [6,10] and [8,12] merge to [6,12]."
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
gift_card_value = 100

def suggest_pair(prices, gift_card_value, chosen_index):
  # Subtask 1: Find another item whose price equals the remaining gift card balance
  # remaining_balance = gift_card_value - prices[chosen_index]
  # Find and return the index of an item with price equal to remaining_balance

  return None

def find_all_pairs(prices, gift_card_value):
  # Subtask 2: Return all pairs of item indices whose prices add up exactly to the gift card value

  return []

def find_highest_pair(prices, gift_card_value):
  #  Subtask 3: Find the pair (by indices) that includes the highest individual item price among all valid pairs
  #  Return empty list [] if no valid pairs exist
    
  return []

# Example usage:
print(suggest_pair(prices, gift_card_value, 1))
print(find_all_pairs(prices, gift_card_value))
print(find_highest_pair(prices, gift_card_value))
                `;

        // Boilerplate code for Gift Card Purchase Assistant (Java)
        const giftCardBoilerplateJava = `import java.util.*;

public class GiftCardAssistant {
    public static void main(String[] args) {
        int[] prices = {40, 60, 20, 80, 90};
        int giftCardValue = 100;
        
        System.out.println(suggestPair(prices, giftCardValue, 1));
        System.out.println(Arrays.deepToString(findAllPairs(prices, giftCardValue).toArray()));
        System.out.println(Arrays.toString(findHighestPair(prices, giftCardValue)));
    }
    
    public static Integer suggestPair(int[] prices, int giftCardValue, int chosenIndex) {
        // Subtask 1: Find another item whose price equals the remaining gift card balance
        // int remainingBalance = giftCardValue - prices[chosenIndex];
        // Find and return the index of an item with price equal to remainingBalance
        
        return null;
    }
    
    public static List<int[]> findAllPairs(int[] prices, int giftCardValue) {
        // Subtask 2: Return all pairs of item indices whose prices add up exactly to the gift card value
        
        return new ArrayList<>();
    }
    
    public static int[] findHighestPair(int[] prices, int giftCardValue) {
        // Subtask 3: Find the pair (by indices) that includes the highest individual item price among all valid pairs
        // Return empty array if no valid pairs exist
        
        return new int[0];
    }
}
                `;

        // Boilerplate code for Gift Card Purchase Assistant (C++)
        const giftCardBoilerplateCpp = `#include <iostream>
#include <vector>
using namespace std;

int suggestPair(vector<int>& prices, int giftCardValue, int chosenIndex) {
    // Subtask 1: Find another item whose price equals the remaining gift card balance
    // int remainingBalance = giftCardValue - prices[chosenIndex];
    // Find and return the index of an item with price equal to remainingBalance
    
    return -1; // Return -1 if not found
}

vector<vector<int>> findAllPairs(vector<int>& prices, int giftCardValue) {
    // Subtask 2: Return all pairs of item indices whose prices add up exactly to the gift card value
    
    return {};
}

vector<int> findHighestPair(vector<int>& prices, int giftCardValue) {
    // Subtask 3: Find the pair (by indices) that includes the highest individual item price among all valid pairs
    // Return empty vector if no valid pairs exist
    
    return {};
}

int main() {
    vector<int> prices = {40, 60, 20, 80, 90};
    int giftCardValue = 100;
    
    cout << suggestPair(prices, giftCardValue, 1) << endl;
    
    vector<vector<int>> allPairs = findAllPairs(prices, giftCardValue);
    cout << "[";
    for (auto& pair : allPairs) {
        cout << "[" << pair[0] << "," << pair[1] << "]";
    }
    cout << "]" << endl;
    
    vector<int> highestPair = findHighestPair(prices, giftCardValue);
    cout << "[" << highestPair[0] << "," << highestPair[1] << "]" << endl;
    
    return 0;
}
                `;

        // Boilerplate code for Step Tracker Insight (Python)
        const stepTrackerBoilerplate = `steps = [8000, 12000, 10000, 6000, 15000, 9000, 11000]
k = 3
target = 25000

def daily_average(steps):
  #  Subtask 1: Calculate the overall average steps per day across all recorded days

  return 0.0

def best_k_day_streak(steps, k):
  #  Subtask 2: Find the highest average step count within any k consecutive days

  return 0.0

def shortest_target_subarray(steps, target):
  #  Subtask 3: Find the shortest contiguous subarray where the total steps is at least the target
  #  Return the length of the shortest subarray, or 0 if no such subarray exists

  return 0

# Example usage:
print(f"Daily average: {daily_average(steps)}")
print(f"Best {k}-day streak average: {best_k_day_streak(steps, k)}")
print(f"Shortest subarray length for target {target}: {shortest_target_subarray(steps, target)}")
                `;

        // Boilerplate code for Step Tracker Insight (Java)
        const stepTrackerBoilerplateJava = `import java.util.*;

public class StepTrackerInsight {
    public static void main(String[] args) {
        int[] steps = {8000, 12000, 10000, 6000, 15000, 9000, 11000};
        int k = 3;
        int target = 25000;
        
        System.out.printf("Daily average: %.2f%n", dailyAverage(steps));
        System.out.printf("Best %d-day streak average: %.2f%n", k, bestKDayStreak(steps, k));
        System.out.printf("Shortest subarray length for target %d: %d%n", target, shortestTargetSubarray(steps, target));
    }
    
    public static double dailyAverage(int[] steps) {
        // Subtask 1: Calculate the overall average steps per day across all recorded days
        
        return 0.0;
    }
    
    public static double bestKDayStreak(int[] steps, int k) {
        // Subtask 2: Find the highest average step count within any k consecutive days
        
        return 0.0;
    }
    
    public static int shortestTargetSubarray(int[] steps, int target) {
        // Subtask 3: Find the shortest contiguous subarray where the total steps is at least the target
        // Return the length of the shortest subarray, or 0 if no such subarray exists
        
        return 0;
    }
}
                `;

        // Boilerplate code for Step Tracker Insight (C++)
        const stepTrackerBoilerplateCpp = `#include <iostream>
#include <vector>
#include <iomanip>
using namespace std;

double dailyAverage(vector<int>& steps) {
    // Subtask 1: Calculate the overall average steps per day across all recorded days
    
    return 0.0;
}

double bestKDayStreak(vector<int>& steps, int k) {
    // Subtask 2: Find the highest average step count within any k consecutive days
    
    return 0.0;
}

int shortestTargetSubarray(vector<int>& steps, int target) {
    // Subtask 3: Find the shortest contiguous subarray where the total steps is at least the target
    // Return the length of the shortest subarray, or 0 if no such subarray exists
    
    return 0;
}

int main() {
    vector<int> steps = {8000, 12000, 10000, 6000, 15000, 9000, 11000};
    int k = 3;
    int target = 25000;
    
    cout << fixed << setprecision(2);
    cout << "Daily average: " << dailyAverage(steps) << endl;
    cout << "Best " << k << "-day streak average: " << bestKDayStreak(steps, k) << endl;
    cout << "Shortest subarray length for target " << target << ": " << shortestTargetSubarray(steps, target) << endl;
    
    return 0;
}
                `;

        // Boilerplate code for Meeting Room Scheduler (Python)
        const meetingRoomBoilerplate = `intervals = [[1,4],[6,10],[2,5],[8,12]]

def longest_meeting(intervals):
  #  Subtask 1: Find the meeting with the longest duration

  return []

def detect_conflicts(intervals):
  #  Subtask 2: Identify all pairs of meetings that have overlapping time intervals

  return []

def merge_overlapping(intervals):
  #  Subtask 3: Merge all overlapping or adjacent meeting intervals into a single interval

  return []

# Example usage:
print(f"Longest meeting: {longest_meeting(intervals)}")
print(f"Conflicting pairs: {detect_conflicts(intervals)}")
print(f"Merged intervals: {merge_overlapping(intervals)}")
                `;

        // Boilerplate code for Meeting Room Scheduler (Java)
        const meetingRoomBoilerplateJava = `import java.util.*;

public class MeetingRoomScheduler {
    public static void main(String[] args) {
        int[][] intervals = {{1,4},{6,10},{2,5},{8,12}};
        
        System.out.println("Longest meeting: " + Arrays.toString(longestMeeting(intervals)));
        System.out.println("Conflicting pairs: " + detectConflicts(intervals));
        System.out.println("Merged intervals: " + Arrays.deepToString(mergeOverlapping(intervals).toArray()));
    }
    
    public static int[] longestMeeting(int[][] intervals) {
        // Subtask 1: Find the meeting with the longest duration
        
        return new int[0];
    }
    
    public static List<int[][]> detectConflicts(int[][] intervals) {
        // Subtask 2: Identify all pairs of meetings that have overlapping time intervals
        
        return new ArrayList<>();
    }
    
    public static List<int[]> mergeOverlapping(int[][] intervals) {
        // Subtask 3: Merge all overlapping or adjacent meeting intervals into a single interval
        
        return new ArrayList<>();
    }
}
                `;

        // Boilerplate code for Meeting Room Scheduler (C++)
        const meetingRoomBoilerplateCpp = `#include <iostream>
#include <vector>
using namespace std;

vector<int> longestMeeting(vector<vector<int>>& intervals) {
    // Subtask 1: Find the meeting with the longest duration
    
    return {};
}

vector<vector<vector<int>>> detectConflicts(vector<vector<int>>& intervals) {
    // Subtask 2: Identify all pairs of meetings that have overlapping time intervals
    
    return {};
}

vector<vector<int>> mergeOverlapping(vector<vector<int>>& intervals) {
    // Subtask 3: Merge all overlapping or adjacent meeting intervals into a single interval
    
    return {};
}

int main() {
    vector<vector<int>> intervals = {{1,4},{6,10},{2,5},{8,12}};
    
    vector<int> longest = longestMeeting(intervals);
    cout << "Longest meeting: [" << longest[0] << "," << longest[1] << "]" << endl;
    
    cout << "Conflicting pairs: ";
    vector<vector<vector<int>>> conflicts = detectConflicts(intervals);
    for (auto& conflict : conflicts) {
        cout << "[[" << conflict[0][0] << "," << conflict[0][1] << "],[" 
             << conflict[1][0] << "," << conflict[1][1] << "]]";
    }
    cout << endl;
    
    cout << "Merged intervals: ";
    vector<vector<int>> merged = mergeOverlapping(intervals);
    for (auto& interval : merged) {
        cout << "[" << interval[0] << "," << interval[1] << "]";
    }
    cout << endl;
    
    return 0;
}
                `;

        // Boilerplate code for First Repeated Number (Python)
        const firstRepeatedBoilerplate = `nums = [2, 5, 3, 2, 8, 7]

def first_repeated_number(nums):
  # Return the first number that appears more than once in the list
    
  return None

# Example usage:
print(first_repeated_number(nums))
                `;

        // Boilerplate code for First Repeated Number (Java)
        const firstRepeatedBoilerplateJava = `import java.util.*;

public class FirstRepeatedNumber {
    public static void main(String[] args) {
        int[] nums = {2, 5, 3, 2, 8, 7};
        
        System.out.println(firstRepeatedNumber(nums));
    }
    
    public static Integer firstRepeatedNumber(int[] nums) {
        // Return the first number that appears more than once in the list
        
        return null;
    }
}
                `;

        // Boilerplate code for First Repeated Number (C++)
        const firstRepeatedBoilerplateCpp = `#include <iostream>
#include <vector>
using namespace std;

int firstRepeatedNumber(vector<int>& nums) {
    // Return the first number that appears more than once in the list
    // Return -1 if no number repeats (since we can't return None in C++)
    
    return -1;
}

int main() {
    vector<int> nums = {2, 5, 3, 2, 8, 7};
    
    int result = firstRepeatedNumber(nums);
    if (result == -1) {
        cout << "None" << endl;
    } else {
        cout << result << endl;
    }
    
    return 0;
}
                `;

        const problemBoilerplates = {
            python: [
                firstRepeatedBoilerplate, // First Repeated Number
                giftCardBoilerplate, // Gift Card Purchase Assistant
                stepTrackerBoilerplate, // Step Tracker Insight
                meetingRoomBoilerplate // Meeting Room Scheduler
            ],
            java: [
                firstRepeatedBoilerplateJava, // First Repeated Number
                giftCardBoilerplateJava, // Gift Card Purchase Assistant
                stepTrackerBoilerplateJava, // Step Tracker Insight
                meetingRoomBoilerplateJava // Meeting Room Scheduler
            ],
            cpp: [
                firstRepeatedBoilerplateCpp, // First Repeated Number
                giftCardBoilerplateCpp, // Gift Card Purchase Assistant
                stepTrackerBoilerplateCpp, // Step Tracker Insight
                meetingRoomBoilerplateCpp // Meeting Room Scheduler
            ]
        };

        const currentProblem = computed(() => problems.value[selectedProblem.value])

        const showResetPopup = ref(false)
        let pendingProblemIndex = null

        const onProblemChange = () => {
            showResetPopup.value = true
            pendingProblemIndex = selectedProblem.value
        }

        const confirmReset = (shouldReset) => {
            showResetPopup.value = false
            if (pendingProblemIndex !== null) {
                emit('problem-changed', {
                    problemIndex: pendingProblemIndex,
                    problem: problems.value[pendingProblemIndex]
                })
                if (shouldReset) {
                    const languageTemplates = problemBoilerplates[props.language]
                    if (languageTemplates && languageTemplates[pendingProblemIndex]) {
                        emit('boilerplate-changed', languageTemplates[pendingProblemIndex])
                    }
                }
                pendingProblemIndex = null
            }
        }

        // Emit initial problem on mount
        onMounted(() => {
            emit('problem-changed', {
                problemIndex: selectedProblem.value,
                problem: currentProblem.value
            })
        })

        watch(() => props.selectedProblem, (newVal) => {
            selectedProblem.value = newVal
        })

        return {
            selectedProblem,
            problems,
            currentProblem,
            onProblemChange,
            showResetPopup,
            confirmReset
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
    position: relative;
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

.reset-popup {
    position: absolute;
    top: 110%;
    right: 0;
    left: auto;
    min-width: 320px;
    max-width: 420px;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    padding: 1rem 1.25rem;
    z-index: 10;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.75rem;
    font-size: 1em;
    white-space: pre-line;
    word-break: break-word;
}
.reset-popup span {
    margin-bottom: 0.5rem;
    line-height: 1.5;
    text-align: right;
}
.reset-popup-buttons {
    display: flex;
    flex-direction: row;
    gap: 0.5rem;
    width: 100%;
    justify-content: flex-end;
}
.reset-popup button {
    background: #6366f1;
    color: #fff;
    border: none;
    border-radius: 4px;
    padding: 0.35rem 1.1rem;
    cursor: pointer;
    font-size: 1em;
    margin-right: 0;
}
.reset-popup button:last-child {
    background: #e5e7eb;
    color: #1f2937;
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
