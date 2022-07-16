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

odoo.define("prt_mail_messages_pro.Chatter", function (require) {
    "use strict";

    var Chatter = require("mail.Chatter");

    Chatter.include({
        // Events
        events: _.extend(Chatter.prototype.events, {
            // Cetmix events
            "click .notif_checkbox": "_onCheckboxClick",
            "click .note_checkbox": "_onCheckboxClick",
            "click .message_checkbox": "_onCheckboxClick",
        }),

        // Start
        start: function () {
            this.getMessageFilters();
            return this._super.apply(this, arguments);
        },

        // Update
        update: function (record, fieldNames) {
            // Get filters if we switch to another record
            if (this.record.res_id !== record.res_id) {
                this.getMessageFilters(record.res_id);
            }
            return this._super.apply(this, arguments);
        },

        /* Get message filters
            When browsing records in form view need to pass id of the next record explicitly.
            Because thread.res_id still contains the id of the previous record
        */
        getMessageFilters: function (res_id) {
            var self = this;
            if (
                typeof this.fields.thread !== typeof undefined &&
                this.fields.thread !== false
            ) {
                if (
                    typeof this.fields.thread.res_id !== typeof undefined &&
                    this.fields.thread.res_id !== false
                ) {
                    const record_id = res_id || this.fields.thread.res_id;
                    this._rpc({
                        model: this.fields.thread.model,
                        method: "read",
                        args: [
                            [record_id],
                            ["hide_notifications", "hide_notes", "hide_messages"],
                        ],
                    }).then(function (result) {
                        var res = result[0];
                        self.$(".notif_checkbox").prop(
                            "checked",
                            !res.hide_notifications
                        );
                        self.$(".note_checkbox").prop("checked", !res.hide_notes);
                        self.$(".message_checkbox").prop("checked", !res.hide_messages);

                        _.extend(self.fields.thread._documentThread, {
                            hide_notifications: res.hide_notifications,
                            hide_notes: res.hide_notes,
                            hide_messages: res.hide_messages,
                        });
                    });
                }
            }
        },

        // Click any of checkbox
        _onCheckboxClick: function (event) {
            var self = this;
            var hide = !event.target.checked;
            var fieldName = "hide_messages";
            if (event.target.className === "btn btn-link notif_checkbox") {
                fieldName = "hide_notifications";
            } else if (event.target.className === "btn btn-link note_checkbox") {
                fieldName = "hide_notes";
            }
            // Write to db
            this._rpc({
                model: this.fields.thread.model,
                method: "write",
                args: [[this.fields.thread.res_id], {[fieldName]: hide}],
            }).then(function () {
                // Save state
                _.extend(self.fields.thread._documentThread, {[fieldName]: hide});

                // Update thread in value if there are deleted messages
                var hasDeleted =
                    self.fields.thread._documentThread.deletedMessageIDs || false;
                if (hasDeleted) {
                    self.fields.thread.value.res_ids =
                        self.fields.thread._documentThread._messageIDs;
                    self.fields.thread._documentThread.deletedMessageIDs = false;
                }

                // Self.fields.thread._fetchMessages({forceFetch: true})
                // self.update(self.fields.thread.record);
                self.trigger_up("reload");
            });
            event.stopPropagation();
        },
    });
});
