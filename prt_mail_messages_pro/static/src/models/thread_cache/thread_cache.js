/** @odoo-module **/

import {registerInstancePatchModel} from "@mail/model/model_core";

registerInstancePatchModel(
    "mail.thread_cache",
    "prt_mail_messages_pro/static/src/models/thread_cache/thread_cache.js",
    {
        async _loadMessages({limit = 30, maxId, minId} = {}) {
            var self = this;
            this.thread.setDefaultThreadFilters();
            if ("web_action" in this.env.session) {
                this.thread.fetchMessagesParams.context =
                    this.env.session["web_action"];
            }
            const messages = await this._super.apply(this, arguments);
            this.thread.applyThreadFilters();
            _.each(messages, function (message) {
                var chatter = self.env.services.messaging.modelManager.models[
                    "mail.chatter"
                ].find((chatter) => chatter.previewMessageId === message.id);
                if (chatter) {
                    message.update({
                        _cx_display_document_link: true,
                    });
                }
            });
            return messages;
        },
    }
);
