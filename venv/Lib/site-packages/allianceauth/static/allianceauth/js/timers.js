/* global moment */

/**
 * Get a duration string like countdown.js
 * e.g. "1y 2d 3h 4m 5s"
 *
 * @param duration
 * @returns {string}
 */
const getDurationString = (duration) => { // eslint-disable-line no-unused-vars
    'use strict';

    let out = '';

    if (duration.years()) {
        out += `${duration.years()}y `;
    }

    if (duration.months()) {
        out += `${duration.months()}m `;
    }

    if (duration.days()) {
        out += `${duration.days()}d `;
    }

    return `${out + duration.hours()}h ${duration.minutes()}m ${duration.seconds()}s`;
};

/**
 * returns the current EVE time as a formatted string
 *
 * condition:
 *     only if moment.js is loaded before,
 *     if not, this function returns an empty string to avoid JS errors from happening.
 *
 * @returns {string}
 */
const getCurrentEveTimeString = () => { // eslint-disable-line no-unused-vars
    'use strict';

    let returnValue = '';

    if (window.moment) {
        returnValue = moment().utc().format('dddd LL HH:mm:ss');
    }

    return returnValue;
};
