# =============================================================================
# modules/networking/flow_logs.tf
# =============================================================================

#===============================================================================
# KMS Key for VPC Flow Logs encryption
#===============================================================================

resource "aws_kms_key" "flow_logs" {
  count                   = var.enable_flow_logs ? 1 : 0
  description             = "KMS key for VPC Flow Logs encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  
  policy = data.aws_iam_policy_document.flow_logs_kms_policy[0].json

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-flow-logs-kms"
  })
}

resource "aws_kms_alias" "flow_logs" {
  count         = var.enable_flow_logs ? 1 : 0
  name          = "alias/${var.project_name}-${var.environment}-flow-logs"
  target_key_id = aws_kms_key.flow_logs[0].key_id
}

#===============================================================================
# CloudWatch Log Group for VPC Flow Logs
#===============================================================================

resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  count             = var.enable_flow_logs ? 1 : 0
  name              = "/aws/vpc/flowlogs/${var.project_name}-${var.environment}"
  retention_in_days = var.flow_logs_retention_days
  kms_key_id        = aws_kms_key.flow_logs[0].arn

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-vpc-flow-logs"
  })
}

#===============================================================================
# IAM Role for VPC Flow Logs
#===============================================================================

resource "aws_iam_role" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0
  name  = "${var.project_name}-${var.environment}-vpc-flow-logs-role"

  assume_role_policy = data.aws_iam_policy_document.flow_logs_assume_role[0].json

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-vpc-flow-logs-role"
  })
}

resource "aws_iam_role_policy" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0
  name  = "${var.project_name}-${var.environment}-vpc-flow-logs-policy"
  role  = aws_iam_role.flow_logs[0].id

  policy = data.aws_iam_policy_document.flow_logs_policy[0].json
}

#===============================================================================
# VPC Flow Logs
#===============================================================================

resource "aws_flow_log" "vpc" {
  count           = var.enable_flow_logs ? 1 : 0
  iam_role_arn    = aws_iam_role.flow_logs[0].arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_logs[0].arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-vpc-flow-logs"
  })
}