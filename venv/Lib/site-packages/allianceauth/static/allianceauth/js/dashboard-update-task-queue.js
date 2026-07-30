/* global fetchGet, numberFormatter, taskQueueSettings */

$(document).ready(() => {
    'use strict';

    const elements = {
        total: document.getElementById('total-task-count'),
        uptime: document.getElementById('celery-uptime'),
        running: document.getElementById('running-task-count'),
        queued: document.getElementById('queued-tasks-count'),
        succeeded: document.getElementById('succeeded-tasks-count'),
        retried: document.getElementById('retried-tasks-count'),
        failed: document.getElementById('failed-tasks-count')
    };

    /**
     * Fetches the task queue status and updates the UI elements accordingly.
     * It retrieves the total number of tasks, running tasks, queued tasks,
     * succeeded tasks, retried tasks, and failed tasks, and updates the
     * corresponding HTML elements with the fetched data.
     * It also updates the progress bars for succeeded, retried, and failed tasks.
     * The function is called immediately and then every 30 seconds to keep the
     * task queue status up to date.
     */
    const updateTaskCount = () => {
        fetchGet({url: taskQueueSettings.url})
            .then((data) => {
                const elemProgressBar = document.getElementById('celery-tasks-progress-bar');
                const progressElements = {
                    succeeded: {
                        bar: document.getElementById('celery-progress-bar-succeeded'),
                        text: document.getElementById('celery-progress-bar-succeeded-progress')
                    },
                    retried: {
                        bar: document.getElementById('celery-progress-bar-retried'),
                        text: document.getElementById('celery-progress-bar-retried-progress')
                    },
                    failed: {
                        bar: document.getElementById('celery-progress-bar-failed'),
                        text: document.getElementById('celery-progress-bar-failed-progress')
                    }
                };

                // Assign progress data from the fetched data to variables
                const {
                    earliest_task: earliestTask,
                    tasks_total: tasksTotal,
                    tasks_running: tasksRunning,
                    tasks_queued: tasksQueued,
                    tasks_succeeded: tasksSucceeded,
                    tasks_retried: tasksRetried,
                    tasks_failed: tasksFailed
                } = data;

                /**
                 * Updates the text content of the specified HTML element with the given value.
                 * If the value is null, it sets the text to 'N/A'.
                 * Otherwise, it formats the number using the locale-specific format.
                 *
                 * @param {HTMLElement} element The HTML element to update.
                 * @param {number|null} value The value to set in the element.
                 */
                const updateTaskCount = (element, value) => {
                    element.textContent = value === null ? taskQueueSettings.l10n.na : numberFormatter({value: value, locales: taskQueueSettings.l10n.language});
                };

                /**
                 * Calculates the time since the given timestamp and returns a formatted string.
                 * If the timestamp is null or undefined, it returns 'N/A'.
                 * The returned string is in the format of "X hours, Y minutes" or "X minutes, Y seconds".
                 *
                 * @param {string|null} timestamp The timestamp to calculate the time since.
                 * @returns {string} A formatted string representing the time since the timestamp.
                 */
                const timeSince = (timestamp) => {
                    if (!timestamp) {
                        return taskQueueSettings.l10n.na;
                    }

                    const diffSecs = Math.floor((Date.now() - new Date(timestamp)) / 1000);

                    if (diffSecs >= 3600) {
                        const hours = Math.floor(diffSecs / 3600);
                        const minutes = Math.floor((diffSecs % 3600) / 60);

                        if (minutes > 0) {
                            const hourText = hours === 1 ? taskQueueSettings.l10n.hour_singular : taskQueueSettings.l10n.hour_plural;
                            const minuteText = minutes === 1 ? taskQueueSettings.l10n.minute_singular : taskQueueSettings.l10n.minute_plural;

                            return `${hours} ${hourText}, ${minutes} ${minuteText}`;
                        }

                        const hourText = hours === 1 ? taskQueueSettings.l10n.hour_singular : taskQueueSettings.l10n.hour_plural;

                        return `${hours} ${hourText}`;
                    }

                    const units = [
                        [
                            60,
                            taskQueueSettings.l10n.minute_singular,
                            taskQueueSettings.l10n.minute_plural
                        ],
                        [
                            1,
                            taskQueueSettings.l10n.second_singular,
                            taskQueueSettings.l10n.second_plural
                        ]
                    ];

                    for (const [seconds, singular, plural] of units) {
                        const value = Math.floor(diffSecs / seconds);

                        if (value > 0) {
                            return `${value} ${value > 1 ? plural : singular}`;
                        }
                    }

                    return `0 ${taskQueueSettings.l10n.second_plural}`;
                };

                /**
                 * Updates the progress bar element and its text content based on the given value and total.
                 * It calculates the percentage of completion and updates the aria attributes and styles accordingly.
                 *
                 * @param {HTMLElement} element The progress bar element to update.
                 * @param {HTMLElement} textElement The text element to update with the percentage.
                 * @param {number} value The current value to set in the progress bar.
                 * @param {number} total The total value for calculating the percentage.
                 */
                const updateProgressBar = (element, textElement, value, total) => {
                    const percentage = total ? (value / total) * 100 : 0;

                    element.setAttribute('aria-valuenow', percentage.toString());
                    textElement.textContent = `${numberFormatter({value: percentage.toFixed(0), locales: taskQueueSettings.l10n.language})}%`;
                    element.style.width = `${percentage}%`;
                };

                // Update task counts
                [
                    [elements.total, tasksTotal],
                    [elements.running, tasksRunning],
                    [elements.queued, tasksQueued],
                    [elements.succeeded, tasksSucceeded],
                    [elements.retried, tasksRetried],
                    [elements.failed, tasksFailed]
                ].forEach(([element, value]) => {
                    updateTaskCount(element, value);
                });

                // Update uptime
                elements.uptime.textContent = timeSince(earliestTask);

                // Update progress bar title
                const [
                    titleTextSucceeded,
                    titleTextRetried,
                    titleTextFailed
                ] = [
                    [tasksSucceeded, taskQueueSettings.l10n.succeeded],
                    [tasksRetried, taskQueueSettings.l10n.retried],
                    [tasksFailed, taskQueueSettings.l10n.failed]
                ].map(([count, label]) => {
                    return `${numberFormatter({value: count, locales: taskQueueSettings.l10n.language})} ${label}`;
                });

                // Set the title attribute for the progress bar
                elemProgressBar.setAttribute(
                    'title',
                    `${titleTextSucceeded}, ${titleTextRetried}, ${titleTextFailed}`
                );

                // Update progress bars
                [
                    tasksSucceeded,
                    tasksRetried,
                    tasksFailed
                ].forEach((count, index) => {
                    const type = ['succeeded', 'retried', 'failed'][index];

                    updateProgressBar(
                        progressElements[type].bar,
                        progressElements[type].text,
                        count,
                        tasksTotal
                    );
                });
            })
            .catch((error) => {
                console.error('Error fetching task queue:', error);

                // If there is an error fetching the task queue, set all elements to 'ERROR'
                [
                    elements.running,
                    elements.queued,
                    elements.succeeded,
                    elements.retried,
                    elements.failed
                ].forEach((elem) => {
                    elem.textContent = taskQueueSettings.l10n.error;
                });
            });
    };

    updateTaskCount();
    setInterval(updateTaskCount, 30000);
});
