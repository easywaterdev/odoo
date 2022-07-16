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

odoo.define("prt_mail_messages_pro.Message", function (require) {
    "use strict";

    var Message = require("mail.model.Message");

    Message.include({
        // Set initial data
        init: function (parent, data, emojis) {
            this._super.apply(this, arguments);
            this._cx_edit_message = data.cx_edit_message;
        },

        // Move message
        moveMessage: function (oldThreadID, newThreadID, oldRecData, newRecData) {
            var mailBus = this.call("mail_service", "getMailBus");
            var oldThread = this.call("mail_service", "getThread", oldThreadID);
            var message_id = this._id;

            // Remove message from old thread
            if (oldThread) {
                oldThread._messageIDs = _.reject(oldThread._messageIDs, function (id) {
                    return id === message_id;
                });
                oldThread._messages = _.reject(oldThread._messages, function (msg) {
                    return msg._id === message_id;
                });
            }

            // Add message to new thread
            var newThread = this.call("mail_service", "getThread", newThreadID);

            if (newThread) {
                this._documentModel = newRecData[0];
                this._documentID = newRecData[1];
                this._threadIDs.push(newThreadID);
                newThread._messageIDs.push(message_id);
                newThread._messages.push(this);
            }

            mailBus.trigger("update_message", this);

            // Remove old thread if from message
            this._threadIDs = _.reject(this._threadIDs, function (thread) {
                return thread === oldThreadID;
            });
        },
    });
});
