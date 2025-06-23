# =============================================================================
# modules/networking/subnets.tf
# =============================================================================

#===============================================================================
# Public Subnets (for ALB, NAT Gateway)
#===============================================================================

resource "aws_subnet" "public" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.public_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]
  
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-public-subnet-${count.index + 1}"
    Type = "Public"
    Tier = "Web"
    AZ   = var.availability_zones[count.index]
  })
}

#===============================================================================
# Private Subnets (for Application/ECS)
#===============================================================================

resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-private-subnet-${count.index + 1}"
    Type = "Private"
    Tier = "Application"
    AZ   = var.availability_zones[count.index]
  })
}

#===============================================================================
# Database Subnets (for RDS)
#===============================================================================

resource "aws_subnet" "database" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.database_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-db-subnet-${count.index + 1}"
    Type = "Database"
    Tier = "Data"
    AZ   = var.availability_zones[count.index]
  })
}

#===============================================================================
# Database Subnet Group
#===============================================================================

resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnet-group"
  subnet_ids = aws_subnet.database[*].id

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-db-subnet-group"
  })
}