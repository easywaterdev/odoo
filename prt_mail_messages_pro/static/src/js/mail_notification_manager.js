/**********************************************************************************
* 
*    Copyright (C) Cetmix OÜ
*
*   Odoo Proprietary License v1.0
* 
*   This software and associated files (the "Software") may only be used (executed,
*   modified, executed after modifications) if you have purchased a valid license
*   from the authors, typically via Odoo Apps, or if you have received a written
*   agreement from the authors of the Software (see the COPYRIGHT file).
* 
*   You may develop Odoo modules that use the Software as a library (typically
*   by depending on it, importing it and using its resources), but without copying
*   any source code or material from the Software. You may distribute those
*   modules under the license of your choice, provided that this license is
*   compatible with the terms of the Odoo Proprietary License (For example:
*   LGPL, MIT, or proprietary licenses similar to this one).
* 
*   It is forbidden to publish, distribute, sublicense, or sell copies of the Software
*   or modified copies of the Software.
* 
*   The above copyright notice and this permission notice must be included in all
*   copies or substantial portions of the Software.
* 
*   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
*   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
*   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
*   IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
*   DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
*   ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
*   DEALINGS IN THE SOFTWARE.
*
**********************************************************************************/

odoo.define("prt_mail_messages_pro.MailNotificationManager", function (require) {
    "use strict";

    var MailNotificationManager = require("mail.Manager.Notification");

    MailNotificationManager.include({
        // Handle notification
        _handlePartnerNotification: function (data) {
            if (data.type === "move_messages") {
                this._handlePartnerMessagesMove(data);
            } else if (data.type === "edit_message") {
                this._handlePartnerMessageEdit(data);
            } else {
                this._super.apply(this, arguments);
            }
        },

        // Move messages
        _handlePartnerMessagesMove: function (data) {
            var self = this;
            // TODO get old_thread_id from data and pass it to moveMessage()
            _.each(data.message_moved_ids, function (movedMessage) {
                var message = self.getMessage(movedMessage[0]);
                if (message) {
                    message.moveMessage(
                        movedMessage[1],
                        movedMessage[2],
                        movedMessage[3],
                        movedMessage[4]
                    );
                }
            });
        },

        // Edit Message
        _handlePartnerMessageEdit: function (data) {
            var mailBus = this.call("mail_service", "getMailBus");
            var message_id = data.message_id;
            var message = this.getMessage(message_id);

            if (message) {
                this._rpc({
                    model: "mail.message",
                    method: "read",
                    args: [[message_id], ["body", "cx_edit_message"]],
                }).then(function (result) {
                    var res = result[0];
                    message._body = res.body;
                    message._cx_edit_message = res.cx_edit_message;
                    mailBus.trigger("update_message", message);
                });
            }
        },

        _handlePartnerMessageDeletionNotification: function (data) {
            var self = this;
            var mailBus = this.call("mail_service", "getMailBus");
            this._super(data);
            _.each(data.message_ids, function (messageID) {
                var message = self.getMessage(messageID);
                if (message) {
                    mailBus.trigger("delete_message", message);
                }
            });
        },
    });
});
