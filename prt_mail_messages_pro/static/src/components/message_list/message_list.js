/** @odoo-modules **/

import {MessageList} from "@mail/components/message_list/message_list";

Object.assign(MessageList.props, {
    previewMessageId: {
        type: Number,
        optional: true,
    },
});

Object.defineProperty(MessageList.props, "previewMessageId", {
    value: {
        type: Number,
        optional: true,
    },
    writable: true,
    configurable: true,
    enumerable: true,
});
