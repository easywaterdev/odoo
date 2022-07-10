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

odoo.define("prt_mail_messages_pro.mail_message_preview_tree", function (require) {
    "use strict";

    var view_registry = require("web.view_registry");
    var ListView = require("web.ListView");
    var ListController = require("web.ListController");
    var ListRenderer = require("web.ListRenderer");
    var Widget = require("web.Widget");
    var Thread = require("mail.widget.Thread");
    var ThreadWidget = require("mail.widget.Thread");
    var DocumentViewer = require("mail.DocumentViewer");

    require("mail.Service");

    var core = require("web.core");

    var _t = core._t;

    var TreeRecordPreview = Widget.extend(Thread.prototype, {
        template: "TreeRecordPreview",
        init: function () {
            this._super.apply(this, arguments);
            this.options = {
                display_needactions: true,
                display_stars: true,
                display_document_link: true,
                display_avatar: true,
                squash_close_messages: true,
                display_email_icon: true,
                display_reply_icon: false,
                areMessageAttachmentsDeletable: false,
            };
        },
        start: function () {
            var self = this;
            this._threadWidget = new ThreadWidget(self, {
                displayOrder: ThreadWidget.ORDER.DESC,
                displayDocumentLinks: true,
                displayMarkAsRead: false,
                squashCloseMessages: false,
            });
            var def1 = this._threadWidget.appendTo(this.$el);
            var def2 = this._super.apply(this, arguments);
            return this.alive($.when(def1, def2));
        },
        render: function (thread, options, record) {
            this.record = record;
            if (thread) {
                options.previewMessageId = record.res_id;
                options = _.defaults(options, this.options);
                this._threadWidget.render(thread, options);
            } else {
                this.renderElement();
                this._threadWidget.appendTo(this.$el);
            }
            this.$el
                .find("a, img, strong, .o_thread_message_avatar, .o_thread_author")
                .click(this._onClickRedirect.bind(this));
            this.$el
                .find(".o_attachment_download")
                .click(this._onAttachmentDownload.bind(this));
            this.$el
                .find(".o_attachment_view")
                .click(this._onAttachmentView.bind(this));
            this.$el
                .find(".o_thread_message")
                .click(this._threadWidget._onClickMessage.bind(this));
            this.$el
                .find(".o_thread_message_star")
                .click(this._onClickMessageStar.bind(this));
            this.$el
                .find(".o_thread_message_reply_composer_quote")
                .click(this._onClickMessageQuote.bind(this));
            this.$el
                .find(".o_thread_message_reply_composer_forward")
                .click(this._onClickMessageForward.bind(this));
            this.$el
                .find(".o_thread_message_reply_composer_move")
                .click(this._onClickMessageMove.bind(this));
            this.$el
                .find(".o_thread_message_reply_composer_delete")
                .click(this._onClickMessageDelete.bind(this));
            this.$el
                .find(".o_thread_message_reply_composer_edit")
                .click(this._onClickMessageEdit.bind(this));
        },
        _onClickRedirect: function (ev) {
            // Ignore inherited branding
            if ($(ev.target).data("oe-field") !== undefined) {
                return;
            }
            var id = $(ev.target).data("oe-id");
            if (id) {
                ev.preventDefault();
                var model = $(ev.target).data("oe-model");
                var options = false;
                if (model && model !== "mail.channel") {
                    options = {
                        model: model,
                        id: id,
                    };
                } else {
                    options = {channelID: id};
                }
                this._redirect(options);
            }
        },
        _onAttachmentDownload: function (ev) {
            ev.stopPropagation();
        },
        _onAttachmentView: function (ev) {
            ev.stopPropagation();
            var activeAttachmentID = $(ev.currentTarget).data("id");
            if (activeAttachmentID) {
                var attachmentViewer = new DocumentViewer(
                    this,
                    this._threadWidget.attachments,
                    activeAttachmentID
                );
                attachmentViewer.appendTo($("body"));
            }
        },
        _onClickMessageStar: function (ev) {
            var message_id = $(ev.currentTarget).data("message-id");
            var message = this.call("mail_service", "getMessage", message_id);
            message.toggleStarStatus();
        },
        _onClickMessageQuote: function (ev) {
            ev.stopPropagation();
            var message_id = $(ev.currentTarget).data("message-id");
            this._threadWidget.reply_composer("quote", message_id);
        },
        _onClickMessageForward: function (ev) {
            ev.stopPropagation();
            var message_id = $(ev.currentTarget).data("message-id");
            this._threadWidget.reply_composer("forward", message_id);
        },
        _onClickMessageMove: function (ev) {
            ev.stopPropagation();
            var message_id = $(ev.currentTarget).data("message-id");
            this._threadWidget.move_composer(message_id);
        },
        _onClickMessageDelete: function (ev) {
            ev.stopPropagation();
            if (confirm(_t("Message will be deleted! Continue?"))) {
                var message_id = $(ev.currentTarget).data("message-id");
                this._rpc({
                    model: "mail.message",
                    method: "unlink_pro",
                    args: [[message_id]],
                });
            }
        },
        _onClickMessageEdit: function (ev) {
            ev.stopPropagation();
            var message_id = $(ev.currentTarget).data("message-id");
            var action = {
                type: "ir.actions.act_window",
                res_model: "cx.message.edit.wiz",
                view_mode: "form",
                view_type: "form",
                views: [[false, "form"]],
                target: "new",
                context: {message_edit_id: message_id},
            };
            this.do_action(action, {});
        },
        _redirect: _.debounce(
            function (options) {
                if ("channelID" in options) {
                    this._onRedirectToChannel(options.channelID);
                } else {
                    this._onRedirect(options.model, options.id);
                }
            },
            500,
            true
        ),
        _onRedirectToChannel: function (channelID) {
            var self = this;
            this.call("mail_service", "joinChannel", channelID).then(function () {
                // Execute Discuss with "channel" as default channel
                self.do_action("mail.action_discuss", {active_id: channelID});
            });
        },
        _onRedirect: function (resModel, resID) {
            this.trigger_up("redirect", {
                res_id: resID,
                res_model: resModel,
            });
        },
    });

    var MessagePreviewListController = ListController.extend({
        custom_events: _.extend({}, ListController.prototype.custom_events, {
            open_preview: "_onOpenPreview",
        }),
        init: function (parent, model, renderer, params) {
            this._super(parent, model, renderer, params);
            // Load from storage
            var data = localStorage[this.modelName + "_previewMode"];
            if (data !== undefined && data !== "") {
                data = JSON.parse(data);
                this.renderer.previewMode = data;
            } else {
                // Preview mode by default
                this.renderer.previewMode = true;
            }
        },
        start: function () {
            var self = this;
            var def1 = this._super.apply(this, arguments);
            this.preview = new TreeRecordPreview(this);
            return this.alive($.when(def1), $.when(this.preview.start())).then(
                function () {
                    if (self.renderer.previewMode) {
                        self.renderPreview(self.$el);
                    }
                    var mailBus = self.call("mail_service", "getMailBus");
                    mailBus.on("update_message", self, self._onUpdateMessage);
                    mailBus.on("delete_message", self, self._onDeleteMessage);
                    mailBus.on("move_message", self, self._onMoveMessage);
                    mailBus.on("update_needaction", self, function () {
                        self.reload();
                    });
                }
            );
        },
        is_action_enabled: function (action) {
            if (action === "preview") {
                return true;
            }
            return this._super(action);
        },
        renderElement: function () {
            this._super.apply(this, arguments);
            if (this.renderer.previewMode) {
                this.$el.addClass("preview-mode");
            } else {
                this.$el.removeClass("preview-mode");
                this.$el.find(".preview_row").removeClass("preview_row");
            }
        },
        renderButtons: function ($node) {
            this._super($node);
            if (!this.noLeaf && this.hasButtons) {
                // Create bootstrap tooltips
                this.$buttons.find(".o_cp_switch_preview").tooltip();
                if (this.renderer.previewMode) {
                    this.$buttons.find(".o_cp_switch_preview").addClass("active");
                }
                this.$buttons.on(
                    "click",
                    ".o_cp_switch_preview",
                    this._onSwitchPreview.bind(this)
                );
            }
        },
        renderPreview($node, record, thread, options) {
            options = options || {};
            this.preview.render(thread, options, record);
            $node.addClass("preview-mode");
            this.preview.$el.appendTo($node);
        },
        _onSwitchPreview: function (event) {
            event.stopPropagation();
            $(event.currentTarget).toggleClass("active");
            $(event.currentTarget).blur();
            this.renderer.switchPreviewMode();
            // Save to local storage
            localStorage[this.modelName + "_previewMode"] = JSON.stringify(
                this.renderer.previewMode
            );
            this.$(".tree-record-preview").remove();
            if (this.renderer.previewMode) {
                this.renderPreview(this.$el);
            } else {
                this.$el.removeClass("preview-mode");
                this.$el.find(".preview_row").removeClass("preview_row");
            }
        },
        _onOpenPreview: function (event) {
            event.stopPropagation();
            var self = this;
            var record_id = event.data.id;
            if (
                this.preview &&
                this.preview.record &&
                this.preview.record.id === record_id
            ) {
                return false;
            }
            // Remove exist preview
            this.$(".tree-record-preview").remove();
            // Get record
            var record = this.model.get(record_id, {raw: true});
            // Create new document thread
            var params = {
                messageIDs: [record.data.id],
                name: record.data.record_name,
                resID: record.data.res_id,
                resModel: record.data.model,
            };
            this.documentThread = this.call(
                "mail_service",
                "getOrAddDocumentThread",
                params
            );
            var fetchDef = this.dp.add(this.documentThread.fetchMessages());
            return fetchDef.then(function () {
                if (!self.documentThread._messages.length) {
                    var message = self.call(
                        "mail_service",
                        "getMessage",
                        self.documentThread._messageIDs[0]
                    );
                    self.documentThread.addMessage(message);
                }
                // Render preview
                self.renderPreview(self.$el, record, self.documentThread);
            });
        },
        _onUpdateMessage: async function (message) {
            var self = this;
            await this.reload();
            if (this.preview && this.preview.record.res_id === message.getID()) {
                var params = {
                    messageIDs: [message.getID()],
                    name: message.getDocumentName(),
                    resID: message.getDocumentID(),
                    resModel: message.getDocumentModel(),
                };
                this.documentThread = this.call(
                    "mail_service",
                    "getOrAddDocumentThread",
                    params
                );
                var fetchDef = this.dp.add(this.documentThread.fetchMessages());
                return fetchDef.then(function () {
                    // Render preview
                    if (!self.documentThread._messages.length) {
                        message = self.call(
                            "mail_service",
                            "getMessage",
                            self.documentThread._messageIDs[0]
                        );
                        self.documentThread.addMessage(message);
                    }
                    self.renderPreview(
                        self.$el,
                        self.preview.record,
                        self.documentThread
                    );
                });
            }
        },
        _onDeleteMessage: function () {
            var self = this;
            return this.reload().then(function () {
                if (self.preview) {
                    // Render empty preview
                    self.renderPreview(self.$el);
                }
            });
        },
        _onMoveMessage: function (message) {
            return this._onUpdateMessage(message);
        },
    });

    var MessagePreviewListRenderer = ListRenderer.extend({
        switchPreviewMode: function () {
            this.previewMode = !this.previewMode;
        },
        _onRowClicked: function (event) {
            this.$el.find(".preview_row").removeClass("preview_row");
            if (this.previewMode) {
                // Open preview
                var id = $(event.currentTarget).data("id");
                if (id) {
                    $(event.currentTarget).addClass("preview_row");
                    this.trigger_up("open_preview", {
                        id: id,
                        target: event.target,
                    });
                }
            } else {
                this._super(event);
            }
        },
    });

    var MessagePreviewListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: MessagePreviewListController,
            Renderer: MessagePreviewListRenderer,
        }),
    });

    view_registry.add("mail_message_preview_tree", MessagePreviewListView);

    return {
        MessagePreviewListController: MessagePreviewListController,
        MessagePreviewListView: MessagePreviewListView,
        MessagePreviewListRenderer: MessagePreviewListRenderer,
    };
});
