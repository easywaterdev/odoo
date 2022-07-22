/** @odoo-module **/

import {
    registerInstancePatchModel,
    registerFieldPatchModel,
} from "@mail/model/model_core";
import {attr} from "@mail/model/model_field";

registerInstancePatchModel(
    "mail.chatter",
    "prt_mail_messages_pro/static/src/models/chatter/chatter.js",
    {
        async saveThreadFilters(currentFilter, currentFilterField) {
            // Save current filters in server
            const filterValue = !this.thread[currentFilter];
            const data = {};
            data[currentFilterField] = filterValue;
            await this.async(() =>
                this.env.services.rpc({
                    model: this.threadModel,
                    method: "save_thread_filter",
                    args: [[this.thread.id], data],
                })
            );
        },

        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickShowNotifications(ev) {
            if (this.thread.displayNotifications) {
                this.thread.update({displayNotifications: false});
            } else {
                this.thread.update({displayNotifications: true});
            }
            this.thread.applyThreadFilters();
        },

        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickShowNotes(ev) {
            if (this.thread.displayNotes) {
                this.thread.update({displayNotes: false});
            } else {
                this.thread.update({displayNotes: true});
            }
            this.thread.applyThreadFilters();
        },

        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickShowMessages(ev) {
            if (this.thread.displayMessages) {
                this.thread.update({displayMessages: false});
            } else {
                this.thread.update({displayMessages: true});
            }
            this.thread.applyThreadFilters();
        },
    }
);
registerFieldPatchModel(
    "mail.chatter",
    "prt_mail_messages_pro/static/src/models/chatter/chatter.js",
    {
        previewMessageId: attr(),
    }
);
