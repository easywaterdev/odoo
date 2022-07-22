/** @odoo-module **/

import {registerInstancePatchModel} from "@mail/model/model_core";

registerInstancePatchModel(
    "mail.message_action_list",
    "prt_mail_messages_pro/static/src/models/message_action_list/message_action_list.js",
    {
        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickMessageQuote(ev) {
            ev.stopPropagation();
            this.message.replyQuote();
        },

        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickMessageForward(ev) {
            ev.stopPropagation();
            this.message.replyForward();
        },

        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickMessageMove(ev) {
            ev.stopPropagation();
            this.message.toMove();
        },

        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickMessageDelete(ev) {
            ev.stopPropagation();
            this.message.toDelete();
        },

        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickMessageEdit(ev) {
            ev.stopPropagation();
            this.message.toEdit();
        },
    }
);
