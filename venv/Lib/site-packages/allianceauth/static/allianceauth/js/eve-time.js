$(document).ready(() => {
    'use strict';

    /**
     * Render the current EVE time in the top menu bar
     * @param element
     */
    const renderClock = (element) => {
        const datetimeNow = new Date();
        const h = String(datetimeNow.getUTCHours()).padStart(2, '0');
        const m = String(datetimeNow.getUTCMinutes()).padStart(2, '0');

        element.html(`${h}:${m}`);
    };

    /**
     * Start the EVE time clock in the top menu bar
     */
    setInterval(() => {
        renderClock($('.eve-time-wrapper .eve-time-clock'));
    }, 500);
});
