/** @odoo-module **/

import {
    registerInstancePatchModel,
    registerFieldPatchModel,
    registerClassPatchModel,
} from "@mail/model/model_core";
import {attr} from "@mail/model/model_field";
import Dialog from "web.Dialog";

registerClassPatchModel(
    "mail.message",
    "prt_mail_messages_pro/static/src/models/message/message.js",
    {
        convertData(data) {
            const data2 = this._super(data);
            if ("cx_edit_message" in data) {
                data2._cx_edit_message = data.cx_edit_message;
            }
            return data2;
        },
    }
);

registerInstancePatchModel(
    "mail.message",
    "prt_mail_messages_pro/static/src/models/message/message.js",
    {
        replyQuote() {
            return this.openReplyAction("quote");
        },
        replyForward() {
            return this.openReplyAction("forward");
        },
        toMove() {
            return this.openMoveAction();
        },
        async toDelete() {
            await this._askDeleteConfirmation();
            await this.async(() =>
                this.env.services.rpc({
                    model: "mail.message",
                    method: "unlink_pro",
                    args: [[this.id]],
                })
            );
        },
        toEdit() {
            this.openEditAction();
        },
        async openReplyAction(mode) {
            const context = await this.async(() =>
                this.env.services.rpc({
                    model: "mail.message",
                    method: "reply_prep_context",
                    args: [[this.id]],
                    kwargs: {
                        context: {
                            wizard_mode: mode,
                        },
                    },
                })
            );
            const action = {
                type: "ir.actions.act_window",
                res_model: "mail.compose.message",
                view_mode: "form",
                views: [[false, "form"]],
                target: "new",
                context: context,
            };
            return this.env.bus.trigger("do-action", {
                action: action,
                options: {
                    on_close: () => {
                        this.originThread.refresh();
                    },
                },
            });
        },
        openMoveAction() {
            const thread = this.threads.find(
                (thread) => thread.model === "mail.channel"
            );
            const action = {
                type: "ir.actions.act_window",
                res_model: "prt.message.move.wiz",
                view_mode: "form",
                views: [[false, "form"]],
                target: "new",
                context: {
                    thread_message_id: this.id,
                    old_thread_id: (thread && thread.id) || null,
                },
            };
            return this.env.bus.trigger("do-action", {action: action});
        },
        openEditAction() {
            const action = {
                type: "ir.actions.act_window",
                res_model: "cx.message.edit.wiz",
                view_mode: "form",
                views: [[false, "form"]],
                target: "new",
                context: {
                    message_edit_id: this.id,
                },
            };
            return this.env.bus.trigger("do-action", {action: action});
        },
        openRelatedRecord() {
            const action = {
                type: "ir.actions.act_window",
                res_model: this.originThread.model,
                res_id: this.originThread.id,
                views: [[false, "form"]],
                target: "current",
            };
            return this.env.bus.trigger("do-action", {action: action});
        },
        _askDeleteConfirmation() {
            return new Promise((resolve) => {
                Dialog.confirm(
                    this,
                    this.env._t(
                        "Message will be deleted! Are you sure you want to delete?"
                    ),
                    {
                        buttons: [
                            {
                                text: this.env._t("Delete"),
                                classes: "btn-primary",
                                close: true,
                                click: resolve,
                            },
                            {
                                text: this.env._t("Discard"),
                                close: true,
                            },
                        ],
                    }
                );
            });
        },
    }
);

registerFieldPatchModel(
    "mail.message",
    "prt_mail_messages_pro/static/src/models/message/message.js",
    {
        _cx_edit_message: attr(),
        _cx_display_document_link: attr({
            default: false,
        }),
    }
);
