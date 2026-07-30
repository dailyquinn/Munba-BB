/**
 * Functions and utilities for the Alliance Auth framework.
 */

/* jshint -W097 */
'use strict';

/**
 * Checks if the given item is an array.
 *
 * @usage
 * ```javascript
 * if (isArray(someVariable)) {
 *    console.log('This is an array');
 * } else {
 *    console.log('This is not an array');
 * }
 * ```
 *
 * @param {*} item - The item to check.
 * @returns {boolean} True if the item is an array, false otherwise.
 */
const isArray = (item) => {
    return Array.isArray(item);
};

/**
 * Checks if the given item is a plain object, excluding arrays and dates.
 *
 * @usage
 * ```javascript
 * if (isObject(someVariable)) {
 *    console.log('This is a plain object');
 * } else {
 *    console.log('This is not a plain object');
 * }
 * ```
 *
 * @param {*} item - The item to check.
 * @returns {boolean} True if the item is a plain object, false otherwise.
 */
const isObject = (item) => {
    return (
        item && typeof item === 'object' && !isArray(item) && !(item instanceof Date)
    );
};

/**
 * Fetch data from an ajax URL
 *
 * Do not call this function directly, use `fetchGet` or `fetchPost` instead.
 *
 * @param {string} url The URL to fetch data from
 * @param {string} method The HTTP method to use for the request (default: 'get')
 * @param {string|null} csrfToken The CSRF token to include in the request headers (default: null)
 * @param {string|null} payload The payload (JSON|Object) to send with the request (default: null)
 * @param {boolean} responseIsJson Whether the response is expected to be JSON or not (default: true)
 * @returns {Promise<string>} The fetched data
 * @throws {Error} Throws an error when:
 * - The method is not valid (only `get` and `post` are allowed).
 * - The CSRF token is required but not provided for POST requests.
 * - The payload is not an object when using POST method.
 * - The response status is not OK (HTTP 200-299).
 * - There is a network error or if the response cannot be parsed as JSON.
 */
const _fetchAjaxData = async ({
    url,
    method = 'get',
    csrfToken = null,
    payload = null,
    responseIsJson = true
}) => {
    const normalizedMethod = method.toLowerCase();

    // Validate the method
    const validMethods = ['get', 'post'];

    if (!validMethods.includes(normalizedMethod)) {
        throw new Error(`Invalid method: ${method}. Valid methods are: get, post`);
    }

    const headers = {};

    // Set headers based on response type
    if (responseIsJson) {
        headers['Accept'] = 'application/json'; // jshint ignore:line
        headers['Content-Type'] = 'application/json';
    }

    let requestUrl = url;
    let body = null;

    if (normalizedMethod === 'post') {
        if (!csrfToken) {
            throw new Error('CSRF token is required for POST requests');
        }

        headers['X-CSRFToken'] = csrfToken;

        if (payload !== null && !isObject(payload)) {
            throw new Error('Payload must be an object when using POST method');
        }

        body = payload ? JSON.stringify(payload) : null;
    } else if (normalizedMethod === 'get' && payload) {
        const queryParams = new URLSearchParams(payload).toString(); // jshint ignore:line

        requestUrl += (url.includes('?') ? '&' : '?') + queryParams;
    }

    /**
     * Throws an error with a formatted message.
     *
     * @param {Response} response The error object containing the message to throw.
     */
    const throwHTTPStatusError = (response) => {
        throw new Error(`Error: ${response.status} - ${response.statusText}`);
    };

    try {
        const response = await fetch(requestUrl, {
            method: method.toUpperCase(),
            headers: headers,
            body: body
        });

        /**
         * Throws an error if the response status is not OK (HTTP 200-299).
         * This is used to handle HTTP errors gracefully.
         */
        if (!response.ok) {
            throwHTTPStatusError(response);
        }

        return responseIsJson ? await response.json() : await response.text();
    } catch (error) {
        // Log the error message to the console
        console.log(`Error: ${error.message}`);

        throw error;
    }
};

/**
 * Fetch data from an ajax URL using the GET method.
 * This function is a wrapper around _fetchAjaxData to simplify GET requests.
 *
 * @usage
 * ```javascript
 * fetchGet({
 *     url: url,
 *     responseIsJson: false
 * }).then((data) => {
 *     // Process the fetched data
 * }).catch((error) => {
 *     console.error(`Error: ${error.message}`);
 *
 *     // Handle the error appropriately
 * });
 * ```
 *
 * @param {string} url The URL to fetch data from
 * @param {string|null} payload The payload (JSON) to send with the request (default: null)
 * @param {boolean} responseIsJson Whether the response is expected to be JSON or not (default: true)
 * @return {Promise<string>} The fetched data
 */
const fetchGet = async ({
    url,
    payload = null,
    responseIsJson = true
}) => {
    return await _fetchAjaxData({
        url: url,
        method: 'get',
        payload: payload,
        responseIsJson: responseIsJson
    });
};

/**
 * Fetch data from an ajax URL using the POST method.
 * This function is a wrapper around _fetchAjaxData to simplify POST requests.
 * It requires a CSRF token for security purposes.
 *
 * @usage
 * ```javascript
 * fetchPost({
 *     url: url,
 *     csrfToken: csrfToken,
 *     payload: {
 *         key: 'value',
 *         anotherKey: 'anotherValue'
 *     },
 *     responseIsJson: true
 * }).then((data) => {
 *     // Process the fetched data
 * }).catch((error) => {
 *     console.error(`Error: ${error.message}`);
 *
 *     // Handle the error appropriately
 * });
 * ```
 *
 * @param {string} url The URL to fetch data from
 * @param {string|null} csrfToken The CSRF token to include in the request headers (default: null)
 * @param {string|null} payload The payload (JSON) to send with the request (default: null)
 * @param {boolean} responseIsJson Whether the response is expected to be JSON or not (default: true)
 * @return {Promise<string>} The fetched data
 */
const fetchPost = async ({
    url,
    csrfToken,
    payload = null,
    responseIsJson = true
}) => {
    return await _fetchAjaxData({
        url: url,
        method: 'post',
        csrfToken: csrfToken,
        payload: payload,
        responseIsJson: responseIsJson
    });
};

/**
 * Recursively merges properties from source objects into a target object. If a property at the current level is an object,
 * and both target and source have it, the property is merged. Otherwise, the source property overwrites the target property.
 * This function does not modify the source objects and prevents prototype pollution by not allowing __proto__, constructor,
 * and prototype property names.
 *
 * @usage
 * ```javascript
 * const target = {a: 1, b: {c: 2}};
 * const source1 = {b: {d: 3}, e: 4 };
 * const source2 = {a: 5, b: {c: 6}};
 *
 * const merged = objectDeepMerge(target, source1, source2);
 *
 * console.log(merged); // {a: 5, b: {c: 6, d: 3}, e: 4}
 * ```
 *
 * @param {Object} target The target object to merge properties into.
 * @param {...Object} sources One or more source objects from which to merge properties.
 * @returns {Object} The target object after merging properties from sources.
 */
function objectDeepMerge (target, ...sources) {
    if (!sources.length) {
        return target;
    }

    // Iterate through each source object without modifying the `sources` array.
    sources.forEach(source => {
        if (isObject(target) && isObject(source)) {
            for (const key in source) {
                if (isObject(source[key])) {
                    if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
                        continue; // Skip potentially dangerous keys to prevent prototype pollution.
                    }

                    if (!target[key] || !isObject(target[key])) {
                        target[key] = {};
                    }

                    objectDeepMerge(target[key], source[key]);
                } else {
                    target[key] = source[key];
                }
            }
        }
    });

    return target;
}

/**
 * Formats a number according to the specified locale.
 * This function uses the Intl.NumberFormat API to format the number.
 *
 * @usage
 * In your Django template get the current language code:
 * ```django
 * {% get_current_language as LANGUAGE_CODE %}
 * ```
 * Then use it in your JavaScript:
 * ```javascript
 * const userLocale = '{{ LANGUAGE_CODE }}'; // e.g., 'en-US', 'de-DE'
 * const number = 1234567.89;
 * const formattedNumber = numberFormatter({
 *     value: number,
 *     locales: userLocale,
 *     options: {
 *         style: 'currency',
 *         currency: 'ISK'
 *     }
 * });
 *
 * // Output will vary based on locale
 * // e.g., '1,234,567.89' for 'en-US', '1.234.567,89' for 'de-DE'
 * console.log(formattedNumber);
 * ```
 *
 * @param {number} value The number to format
 * @param {string | string[]} locales The locale(s) to use for formatting (e.g., 'en-US', 'de-DE', ['en-US', 'de-DE']). If not provided, the browser's default locale will be used and any language settings from the user will be ignored.
 * @param {Object} [options={}] Additional options for number formatting (see `Intl.NumberFormat` documentation - https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/NumberFormat)
 * @return {string} The formatted number as a string
 */
const numberFormatter = ({value, locales, options = {}}) => {
    console.log('Formatting number:', value, 'for locale(s):', locales, 'with options:', options);
    const formatter = new Intl.NumberFormat(locales, {
        maximumFractionDigits: 2,
        minimumFractionDigits: 0,
        ...options
    });

    return formatter.format(value);
};

/**
 * When the document is ready …
 */
$(document).ready(() => {
    /**
     * Prevent double form submits by adding a class to the form
     * when it is submitted.
     *
     * This class can be used to show a visual indicator that the form is being
     * submitted, such as a spinner.
     *
     * This is useful to prevent users from double-clicking the submit button
     * and submitting the form multiple times.
     */
    document.querySelectorAll('form').forEach((form) => {
        form.addEventListener('submit', (e) => {
            // Prevent if already submitting
            if (form.classList.contains('is-submitting')) {
                e.preventDefault();
            }

            // Add class to hook our visual indicator on
            form.classList.add('is-submitting');
        });
    });
});
