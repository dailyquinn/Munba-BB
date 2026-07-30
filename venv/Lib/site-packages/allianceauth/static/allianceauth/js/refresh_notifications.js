/* global notificationUPdateSettings, xhr */

/**
 *  This script refreshed the unread notification count in the top menu
 *  on a regular basis so to keep the user apprized about newly arrived
 *  notifications without having to reload the page.
 *
 *  The refresh rate can be changed via the Django setting NOTIFICATIONS_REFRESH_TIME.
 *  See documentation for details.
 */
$(document).ready(() => {
    'use strict';

    const notificationListViewUrl = notificationUPdateSettings.notificationsListViewUrl;
    const notificationRefreshTime = notificationUPdateSettings.notificationsRefreshTime;
    const userNotificationCountViewUrl = notificationUPdateSettings.userNotificationsCountViewUrl;

    /**
     * Update the notification item in the top menu with the current unread count
     */
    const updateNotifications = () => {
        $.getJSON(userNotificationCountViewUrl, (data, status) => {
            if (status === 'success') {
                let innerHtml;
                const unreadCount = data.unread_count;

                if (unreadCount > 0) {
                    innerHtml = (
                        `Notifications <span class="badge">${unreadCount}</span>`
                    );
                } else {
                    innerHtml = '<i class="fa-solid fa-bell"></i>';
                }

                $('#menu_item_notifications').html(
                    `<a href="${notificationListViewUrl}">${innerHtml}</a>`
                );
            } else {
                console.error(
                    `Failed to load HTMl to render notifications item. Error: ${xhr.status}': '${xhr.statusText}`
                );
            }
        });
    };

    let myInterval;

    /**
     * Activate automatic refreshing of notifications
     */
    const activateRefreshing = () => {
        if (notificationRefreshTime > 0) {
            myInterval = setInterval(
                updateNotifications, notificationRefreshTime * 1000
            );
        }
    };

    /**
     * Deactivate automatic refreshing of notifications
     */
    const deactivateRefreshing = () => {
        if ((notificationRefreshTime > 0) && (typeof myInterval !== 'undefined')) {
            clearInterval(myInterval);
        }
    };

    /**
     * Activate refreshing when the browser tab is active
     * and deactivate it when it is not
     */
    $(document).on({
        'show': () => {
            activateRefreshing();
        },
        'hide': () => {
            deactivateRefreshing();
        }
    });

    /**
     * Initial start of refreshing on script loading
     */
    activateRefreshing();
});
