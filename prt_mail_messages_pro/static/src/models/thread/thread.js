/** @odoo-module **/

import {
    registerInstancePatchModel,
    registerFieldPatchModel,
} from "@mail/model/model_core";
import {attr} from "@mail/model/model_field";

registerInstancePatchModel(
    "mail.thread",
    "prt_mail_messages_pro/static/src/models/thread/thread.js",
    {

        setDefaultThreadFilters() {
            this.update({
                displayNotifications: true,
                displayNotes: true,
                displayMessages: true
            });
        },

        async applyThreadFilters() {
            const messages = this.cache.fetchedMessages || this.messages;
            let filteredMessages = _.clone(messages);
            if (!this.displayNotifications) {
                filteredMessages = _.filter(filteredMessages, function (message) {
                    return (
                        !message.is_notification &&
                        message.message_type !== "notification"
                    );
                });
            }
            if (!this.displayNotes) {
                filteredMessages = _.filter(filteredMessages, function (message) {
                    return !message.is_note;
                });
            }
            if (!this.displayMessages) {
                filteredMessages = _.filter(filteredMessages, function (message) {
                    return !message.is_discussion;
                });
            }
            // Unlink all messages from thread
            this.cache.update({messages: [["unlink", messages]]});
            // Apply filtered messages
            this.cache.update({messages: [["link", filteredMessages]]});
        },
    }
);

registerFieldPatchModel(
    "mail.thread",
    "prt_mail_messages_pro/static/src/models/thread/thread.js",
    {
        displayNotifications: attr({
            default: true,
        }),

        displayNotes: attr({
            default: true,
        }),
        displayMessages: attr({
            default: true,
        }),

    }
);
