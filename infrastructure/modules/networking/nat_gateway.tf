# =============================================================================
# modules/networking/nat_gateway.tf
# =============================================================================

#===============================================================================
# Elastic IPs for NAT Gateways
#===============================================================================

resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? length(var.availability_zones) : 0
  domain = "vpc"

  depends_on = [aws_internet_gateway.main]

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-nat-eip-${count.index + 1}"
    AZ   = var.availability_zones[count.index]
  })
}

#===============================================================================
# NAT Gateways
#===============================================================================

resource "aws_nat_gateway" "main" {
  count         = var.enable_nat_gateway ? length(var.availability_zones) : 0
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  depends_on = [aws_internet_gateway.main]

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-nat-gw-${count.index + 1}"
    AZ   = var.availability_zones[count.index]
  })
}