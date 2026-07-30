$(document).ready(() => {
    'use strict';

    /**
     * Collect all badges in the sidebar menu that are not part of a collapsible submenu, and calculate the total notification count.
     * Show a total notification badge in the navbar if there are any notifications.
     */
    const totalNotificationsBadge = () => {
        const badges = [];
        let notificationCount = 0;

        document.querySelectorAll('#sidebar-menu .badge').forEach(b => {
            const li = b.closest('li');

            if (!li || !li.querySelector('ul.collapse')) {
                badges.push(b);
                notificationCount += parseInt(b.textContent);
            }
        });

        if (badges.length > 0 && notificationCount > 0) {
            const notificationBadge = document.createElement('span');
            notificationBadge.id = "globalNotificationCount";
            notificationBadge.classList.add(
                'badge',
                'text-bg-danger',
                'align-self-center',
                'sidemenu-notification-badge',
                'sidemenu-total-notifications-badge'
            );
            notificationBadge.textContent = String(notificationCount);

            document.querySelector('a.navbar-brand i.fa-solid').prepend(notificationBadge);
        }
    };

    /**
     * Find the active child menu item in the sidebar menu, if any, and ensure its parent submenu is expanded.
     */
    const expandChildMenu = () => {
        const activeChildMenuItem = document.querySelector('ul#sidebar-menu ul.collapse a.active');

        if (activeChildMenuItem) {
            const activeChildMenuUl = activeChildMenuItem.closest('ul');
            activeChildMenuUl.classList.add('show');

            document.querySelectorAll(`[data-bs-target^="#${activeChildMenuUl.id}"]`)
                .forEach(element => element.setAttribute('aria-expanded', 'true'));
        }
    };

    // Execute functions on document ready
    [
        totalNotificationsBadge,
        expandChildMenu
    ].forEach(fn => fn());
});
