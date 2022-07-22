/** @odoo-module **/

import {Message} from "@mail/components/message/message";
import {patch} from "web.utils";

patch(Message, "prt_mail_messages_pro/static/src/models/message/message.js", {
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickOriginThread(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        if (this.messageView.message._cx_display_document_link) {
            this.messageView.message.openRelatedRecord();
        } else {
            this._super(ev);
        }
    },
});
