/** @odoo-module **/

import {
    registerFieldPatchModel,
    registerIdentifyingFieldsPatch,
} from "@mail/model/model_core";
import {attr} from "@mail/model/model_field";
import {ThreadView} from "@mail/components/thread_view/thread_view";

registerFieldPatchModel(
    "mail.thread_viewer",
    "prt_mail_messages_pro/static/src/components/thread_view/thread_view.js",
    {
        previewMessageId: attr({
            default: false,
        }),
    }
);

// registerIdentifyingFieldsPatch("mail.thread_viewer", "qunit", (identifyingFields) => {
//     identifyingFields[0].push("qunitTest");
// });

Object.assign(ThreadView.props, {
    previewMessageId: {
        type: Number,
        optional: true,
    },
});

Object.defineProperty(ThreadView.props, "previewMessageId", {
    value: {
        type: Number,
        optional: true,
    },
    writable: true,
    configurable: true,
    enumerable: true,
});
