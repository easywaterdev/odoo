/** @odoo-module **/

import {insertAndReplace} from "@mail/model/model_field_command";
import {registerInstancePatchModel} from "@mail/model/model_core";

registerInstancePatchModel(
    "mail.messaging_notification_handler",
    "prt_mail_messages_pro/static/src/models/messaging_notification_handler/messaging_notification_handler.js",
    {
        init: function () {
            this._super.apply(this, arguments);
            this.models = this.env.services.messaging.modelManager.models;
        },

        async _handleNotifications(data) {
            data.map((message) => {
                if (message.type === "message_updated") {
                    return this._handleNotificationMessage(message.payload);
                }
            });
            return this._super(data);
        },
        async _handleNotificationMessage({message_ids, action}) {
            for (const msg of message_ids) {
                const message = this.models["mail.message"].find(
                    (message) => message.id === msg.message_id
                );
                if (message) {
                    if (action === "move") {
                        // Original thread
                        const originalThreadData = msg.originalThread;
                        const originalThread = this.models["mail.thread"].find(
                            (thread) =>
                                thread.id === originalThreadData.thread_id &&
                                thread.model === originalThreadData.thread_model
                        );
                        if (originalThread) {
                            // Delete the message from original thread
                            originalThread.cache.update({
                                messages: [["unlink", message]],
                            });
                        }
                        // Moved thread
                        originalThread.cache.update({isCacheRefreshRequested: true});
                        const movedThreadData = msg.movedThread;
                        const movedThread = this.models["mail.thread"].find(
                            (thread) =>
                                thread.id === movedThreadData.thread_id &&
                                thread.model === movedThreadData.thread_model
                        );
                        if (movedThread) {
                            // Add the message to moved thread
                            movedThread.cache.update({
                                messages: [["link", message]],
                            });
                        } else {
                            const movedThreadNew = this.models["mail.thread"].create({
                                composer: insertAndReplace({isLog: false}),
                                id: movedThreadData.thread_id,
                                model: movedThreadData.thread_model,
                            });
                            movedThreadNew.cache.update({
                                messages: [["link", message]],
                            });
                        }
                        this.env.bus.trigger("move_message", message);
                    } else if (action === "edit") {
                        const fields = ["body", "cx_edit_message"];
                        const [data] = await this.async(() =>
                            this.env.services.rpc({
                                model: "mail.message",
                                method: "read",
                                args: [[message.id], fields],
                            })
                        );
                        message.update({
                            body: data.body,
                            _cx_edit_message: data.cx_edit_message,
                        });
                    }
                }
            }
        },
        _handleNotificationMessageDelete({message_ids}) {
            this._super({message_ids});
            this.env.bus.trigger("delete_message");
        },
    }
);
